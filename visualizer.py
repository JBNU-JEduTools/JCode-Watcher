from PIL import Image, ImageDraw, ImageFont
import imageio
import os
from pathlib import Path
import pygments
from pygments import lexers
from pygments.formatters import ImageFormatter
import re
import numpy as np

class CodeVisualizer:
    def __init__(self, snapshot_dir="snapshots", output_dir="gifs"):
        self.snapshot_dir = snapshot_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        self.font_size = 15
        # 고정된 크기 설정
        self.image_width = 1000
        self.image_height = 800
        
    def _sort_snapshots(self, snapshot_files):
        """타임스탬프 기준으로 스냅샷 파일들을 정렬"""
        def extract_timestamp(filepath):
            # Path 객체를 문자열로 변환하여 파일명만 추출
            filename = filepath.name
            match = re.search(r'_(\d{8}_\d{6})', filename)
            return match.group(1) if match else ''
            
        return sorted(snapshot_files, key=extract_timestamp)
    
    def _get_max_lines(self, snapshots):
        """모든 스냅샷 중 가장 긴 코드의 줄 수를 반환"""
        max_lines = 0
        max_line_length = 0
        
        for snapshot in snapshots:
            with open(snapshot, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                max_lines = max(max_lines, len(lines))
                max_line_length = max(max_line_length, max(len(line) for line in lines) if lines else 0)
        
        # 최소 30줄은 보장
        return max(30, max_lines), max_line_length

    def _has_korean(self, text):
        """텍스트에 한글이 포함되어 있는지 확인"""
        return any(ord('가') <= ord(char) <= ord('힣') for char in text)

    def _get_available_fonts(self):
        """코드용 폰트와 한글 폰트를 찾아 반환"""
        # Windows 기준 폰트 경로
        font_paths = {
            'Consolas': 'C:/Windows/Fonts/consola.ttf',
            'D2Coding': 'C:/Windows/Fonts/D2Coding.ttf',
            'NanumGothicCoding': 'C:/Windows/Fonts/NanumGothicCoding.ttf',
            'GulimChe': 'C:/Windows/Fonts/gulimche.ttc',
            'Courier New': 'C:/Windows/Fonts/cour.ttf'
        }
        
        # 기본 코드 폰트 (Consolas)
        default_font = font_paths.get('Consolas')
        if not default_font or not os.path.exists(default_font):
            default_font = font_paths.get('Courier New')  # 폴백 폰트
        
        # 한글 폰트 찾기
        korean_fonts = ['D2Coding', 'NanumGothicCoding', 'GulimChe']
        korean_font = None
        for font in korean_fonts:
            font_path = font_paths.get(font)
            if font_path and os.path.exists(font_path):
                korean_font = font_path
                break
        
        # 한글 폰트가 없으면 기본 폰트 사용
        return default_font, korean_font or default_font

    def _create_code_image(self, code_path, output_path, min_height, max_line_length):
        """코드 파일을 구문 강조된 이미지로 변환"""
        with open(code_path, 'r', encoding='utf-8') as f:
            code = f.read()
            lines = code.splitlines()
            
            # 각 줄을 최대 길이에 맞춰 공백으로 채움
            padded_lines = []
            for line in lines:
                padding = ' ' * (max_line_length - len(line))
                padded_lines.append(line + padding)
            
            # 줄 수가 min_height보다 작으면 빈 줄 추가
            if len(padded_lines) < min_height:
                padding_line = ' ' * max_line_length
                padding_lines = [padding_line] * (min_height - len(padded_lines))
                padded_lines.extend(padding_lines)
            
            code = '\n'.join(padded_lines) + '\n'
        
        # 파일 확장자에 따른 lexer 선택
        lexer = lexers.get_lexer_for_filename(code_path)
        
        # 폰트 선택 (한글이 있는 경우에만 한글 폰트 사용)
        default_font, korean_font = self._get_available_fonts()
        font_name = korean_font if self._has_korean(code) else default_font
        
        # 이미지 생성을 위한 설정
        line_height = self.font_size + 5
        total_height = min_height * line_height + 40
        char_width = self.font_size * 0.6
        total_width = int(max_line_length * char_width + 100)
        
        formatter = ImageFormatter(
                                font_name=font_name,
                                font_size=self.font_size,
                                line_numbers=True,
                                line_number_bg='#eee',
                                line_number_fg='#000',
                                line_number_bold=True,
                                style='monokai',
                                image_pad=20,
                                image_bg='white',
                                line_pad=5,
                                encoding='utf-8',
                                image_width=total_width,
                                image_height=total_height,
                                line_number_chars=4,
                                line_number_pad=8,
                                wrap=False,  # 줄바꿈 비활성화
                                full=True)
        
        # 코드를 이미지로 변환하여 직접 저장
        image_bytes = pygments.highlight(code, lexer, formatter)
        with open(output_path, 'wb') as f:
            f.write(image_bytes)

    def _resize_to_fixed_size(self, image_path):
        """이미지를 고정된 크기로 강제 변환"""
        with Image.open(image_path) as img:
            resized_img = img.resize((self.image_width, self.image_height), Image.Resampling.LANCZOS)
            resized_img.save(image_path)

    def create_animation(self, user_id, file_name):
        """특정 사용자의 특정 파일에 대한 스냅샷들을 애니메이션으로 변환"""
        # 스냅샷 디렉토리 경로
        snapshot_path = Path(self.snapshot_dir) / user_id / file_name
        
        if not snapshot_path.exists():
            print(f"스냅샷 경로를 찾을 수 없습니다: {snapshot_path}")
            return
        
        # 임시 이미지 저장 디렉토리
        temp_dir = Path(self.output_dir) / "temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        # 스냅샷 파일 목록 가져오기 및 정렬
        snapshot_files = [f for f in snapshot_path.glob("*") if f.is_file()]
        sorted_snapshots = self._sort_snapshots(snapshot_files)
        
        if not sorted_snapshots:
            print("스냅샷 파일을 찾을 수 없습니다.")
            return
        
        # 최대 코드 길이 계산
        max_lines, max_line_length = self._get_max_lines(sorted_snapshots)
        
        # 각 스냅샷을 이미지로 변환
        temp_images = []
        for snapshot in sorted_snapshots:
            temp_image = temp_dir / f"temp_{len(temp_images)}.png"
            self._create_code_image(snapshot, temp_image, max_lines, max_line_length)
            temp_images.append(temp_image)
        
        # 모든 이미지를 프레임으로 변환
        frames = []
        first_image_size = None
        
        for temp_image in temp_images:
            with Image.open(temp_image) as img:
                if first_image_size is None:
                    first_image_size = img.size
                    frames.append(np.array(img))
                else:
                    # 첫 번째 이미지 크기에 맞춰 리사이징
                    resized_img = img.resize(first_image_size, Image.Resampling.LANCZOS)
                    frames.append(np.array(resized_img))
        
        # GIF 생성
        output_path = Path(self.output_dir) / f"{user_id}_{file_name}.gif"
        imageio.mimsave(output_path, frames, duration=2.0)
        
        print(f"애니메이션 생성 완료: {output_path}")
        
        # 임시 파일 유지 (삭제 코드 제거)

if __name__ == "__main__":
    visualizer = CodeVisualizer()
    
    # target 디렉토리의 모든 사용자와 파일에 대해 애니메이션 생성
    target_dir = Path("target")
    for user_dir in target_dir.iterdir():
        if user_dir.is_dir():
            user_id = user_dir.name
            # 재귀적으로 모든 .c 파일 찾기
            for c_file in user_dir.rglob("*.c"):
                # 파일 이름만 추출
                file_name = c_file.name
                print(f"Processing: {user_id}/{file_name}")
                visualizer.create_animation(user_id, file_name)
