#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <linux/nsproxy.h>
#include <linux/dcache.h>
#include <linux/fs.h>
#include <linux/fs_struct.h>
#include <linux/mm_types.h>
#include <linux/utsname.h>

#define MAX_PATH_LEN 256
#define ARGSIZE 256
#define UTS_LEN 65
#define MAX_DENTRY_LEVEL 16
#define MAX_DNAME_LEN 64

// 에러 플래그 정의
#define ERR_NONE              0x00000000  // 모든 검사 통과
#define ERR_DENTRY_TOO_DEEP   0x00000001  // dentry 깊이가 MAX_DENTRY_LEVEL 초과
#define ERR_DNAME_TOO_LONG    0x00000002  // 개별 dname 길이가 MAX_DNAME_LEN 초과
#define ERR_ARGS_TOO_LONG     0x00000004  // 명령줄 인수가 ARGSIZE 초과

struct data_t {
    u32 pid;
    u32 error_flags;
    char hostname[UTS_LEN];
    char binary_path[MAX_PATH_LEN];
    char cwd[MAX_PATH_LEN];
    char args[ARGSIZE];
    int binary_path_offset;
    int cwd_offset;
    u32 args_len;
    int exit_code;
};

BPF_PERCPU_ARRAY(tmp_array, struct data_t, 1);
BPF_HASH(process_data, u32, struct data_t);
BPF_PROG_ARRAY(prog_array, 4);
BPF_PERF_OUTPUT(events);

static __always_inline int get_dentry_path(struct dentry *dentry, char *buf, int buf_size, u32 *error_flags)
{
    int pos = buf_size - 1;
    buf[pos] = '\0';

    struct dentry *d = dentry;
    struct dentry *parent;
    
    for (int i = 0; i < MAX_DENTRY_LEVEL && d != NULL; i++) {
        bpf_probe_read(&parent, sizeof(parent), &d->d_parent);
        
        if (d == parent)
            break;

        struct qstr d_name = {};
        bpf_probe_read(&d_name, sizeof(d_name), &d->d_name);

        // dname 길이 검사를 먼저 수행
        if (d_name.len > MAX_DNAME_LEN) {
            *error_flags |= ERR_DNAME_TOO_LONG;
            break;
        }

        char dname[MAX_DNAME_LEN] = {};
        int name_len = bpf_probe_read_str(dname, sizeof(dname), d_name.name);

        if (name_len <= 1)
            break;

        if (pos - (name_len - 1) - 1 < 0)
            break;

        pos -= (name_len - 1);
        bpf_probe_read(&buf[pos], name_len - 1, dname);

        if (pos > 0) {
            pos--;
            buf[pos] = '/';
        }

        d = parent;
        
        // MAX_DENTRY_LEVEL에 도달했지만 아직 루트가 아닌 경우 체크
        if (i == MAX_DENTRY_LEVEL - 1) {
            bpf_probe_read(&parent, sizeof(parent), &d->d_parent);
            if (d != parent) {
                *error_flags |= ERR_DENTRY_TOO_DEEP;
            }
        }
    }

    if (pos == buf_size - 1) {
        pos--;
        buf[pos] = '/';
    }
    
    return pos;
}

// 첫 번째 핸들러: 호스트네임 검증 및 PID 설정
int init_handler(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u32 zero = 0;
    
    struct data_t *tmp = tmp_array.lookup(&zero);
    if (!tmp)
        return 0;
    
    // 기본 정보 설정
    tmp->pid = pid;
    
    // UTS namespace에서 hostname 읽기
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    if (!task)
        return 0;
    
    struct nsproxy *ns = task->nsproxy;
    if (!ns)
        return 0;
    
    struct uts_namespace *uts_ns = ns->uts_ns;
    if (!uts_ns)
        return 0;
    
    // hostname 읽기
    bpf_probe_read_kernel_str(tmp->hostname, UTS_LEN, uts_ns->name.nodename);


    // jcode- 접두어 확인
    if (tmp->hostname[0] != 'j' || 
        tmp->hostname[1] != 'c' ||
        tmp->hostname[2] != 'o' ||
        tmp->hostname[3] != 'd' ||
        tmp->hostname[4] != 'e' ||
        tmp->hostname[5] != '-') {
        return 0;
    }
    
    // 모든 검증을 통과한 경우에만 맵에 등록
    process_data.update(&pid, tmp);
    prog_array.call(ctx, 1);  // binary_handler로
    return 0;
}

// 두 번째 핸들러: 바이너리 경로 수집
int binary_handler(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    struct data_t *data = process_data.lookup(&pid);
    if (!data) {
        process_data.delete(&pid);
        return 0;
    }
    
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    if (!task) {
        process_data.delete(&pid);
        return 0;
    }

    struct mm_struct *mm;
    bpf_probe_read(&mm, sizeof(mm), &task->mm);
    if (!mm) {
        process_data.delete(&pid);
        return 0;
    }

    struct file *exe_file;
    bpf_probe_read(&exe_file, sizeof(exe_file), &mm->exe_file);
    if (!exe_file) {
        process_data.delete(&pid);
        return 0;
    }

    struct path fpath;
    bpf_probe_read(&fpath, sizeof(fpath), &exe_file->f_path);

    data->binary_path_offset = get_dentry_path(
        fpath.dentry,
        data->binary_path,
        sizeof(data->binary_path),
        &data->error_flags
    );

    prog_array.call(ctx, 2);  // cwd_handler로
    return 0;
}

// 세 번째 핸들러: CWD 수집
int cwd_handler(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    struct data_t *data = process_data.lookup(&pid);
    if (!data) {
        process_data.delete(&pid);
        return 0;
    }
    
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    if (!task) {
        process_data.delete(&pid);
        return 0;
    }

    struct fs_struct *fs = NULL;
    bpf_probe_read(&fs, sizeof(fs), &task->fs);
    if (!fs) {
        process_data.delete(&pid);
        return 0;
    }

    struct path pwd = {};
    bpf_probe_read(&pwd, sizeof(pwd), &fs->pwd);
    struct dentry *dentry = pwd.dentry;
    if (!dentry) {
        process_data.delete(&pid);
        return 0;
    }

    data->cwd_offset = get_dentry_path(dentry, data->cwd, sizeof(data->cwd), &data->error_flags);
    
    prog_array.call(ctx, 3);  // args_handler로
    return 0;
}

// 네 번째 핸들러: 명령줄 인수 수집
int args_handler(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    struct data_t *data = process_data.lookup(&pid);
    if (!data) {
        process_data.delete(&pid);
        return 0;
    }
    
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    if (!task) {
        process_data.delete(&pid);
        return 0;
    }
    
    struct mm_struct *mm = task->mm;
    if (!mm || !mm->arg_start) {
        process_data.delete(&pid);
        return 0;
    }
    
    u64 start = (u64)mm->arg_start;
    u64 end   = (u64)mm->arg_end;
    u64 length = 0;

    if (end > start) {
        length = end - start;
    }

    if (length > ARGSIZE) {
        data->error_flags |= ERR_ARGS_TOO_LONG;
        length = ARGSIZE;
    }

    data->args_len = (u32)length;
    bpf_probe_read_user(data->args, length, (void *)start);
    
    // 여기서는 perf_submit 하지 않음
    return 0;
}

// exit 트레이스포인트용 핸들러
int exit_handler(struct pt_regs *ctx) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    
    // process_data에서 해당 PID의 데이터 조회
    struct data_t *data = process_data.lookup(&pid);
    if (!data)  // 컨테이너 프로세스가 아니었거나 exec 데이터 수집에 실패한 경우
        return 0;
    
    // exit code 수집
    struct task_struct *task = (struct task_struct *)bpf_get_current_task();
    if (!task) {
        process_data.delete(&pid);
        return 0;
    }
    
    data->exit_code = task->exit_code >> 8; // 상위 8비트가 실제 exit code
        
    // 데이터를 사용자 공간으로 전송
    events.perf_submit(ctx, data, sizeof(struct data_t));
    
    // 맵에서 데이터 삭제
    process_data.delete(&pid);
    return 0;
} 