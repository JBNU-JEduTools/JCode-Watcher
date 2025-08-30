import pytest
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from app.sender import SnapshotSender
from app.models.source_file_info import SourceFileInfo


class TestSnapshotSender:
    """SnapshotSender 클래스 테스트"""

    @pytest.fixture
    def sender(self):
        """SnapshotSender 인스턴스 생성"""
        return SnapshotSender()

    @pytest.fixture
    def sample_source_file_info(self):
        """테스트용 SourceFileInfo 생성"""
        return SourceFileInfo(
            class_div="os-1",
            hw_name="hw1",
            student_id="202012345",
            filename="main@src@test.c",
            target_file_path=Path("/test/path/main.c")
        )

    def _create_mock_session(self, status_code=200, response_text='{"message": "success"}'):
        """Mock aiohttp session 생성 헬퍼 함수"""
        from unittest.mock import MagicMock
        
        # 일반 Mock을 사용하여 context manager 구현
        mock_response = MagicMock()
        mock_response.status = status_code
        mock_response.text = AsyncMock(return_value=response_text)
        
        # POST 요청의 context manager 
        mock_post_context = MagicMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        # Session mock
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_context)
        
        # ClientSession context manager
        mock_session_context = MagicMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        return mock_session_context, mock_session

    def test_init(self, sender):
        """SnapshotSender 초기화 테스트"""
        assert sender.base_url == "http://localhost:8080"
        assert sender.timeout.total == 20

    @patch('app.sender.settings')
    def test_init_with_custom_settings(self, mock_settings):
        """커스텀 설정으로 초기화 테스트"""
        mock_settings.API_SERVER = "http://test-server:9000/"
        mock_settings.API_TIMEOUT_TOTAL = 30
        
        sender = SnapshotSender()
        
        assert sender.base_url == "http://test-server:9000"
        assert sender.timeout.total == 30

    @pytest.mark.asyncio
    async def test_register_snapshot_success(self, sender, sample_source_file_info):
        """API 요청 성공 테스트"""
        mock_session_context, mock_session = self._create_mock_session()
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await sender.register_snapshot(sample_source_file_info, 1024)
            
            assert result is True
            mock_session.post.assert_called_once()
            
            # 호출된 URL과 데이터 검증 (student_id가 정수로 변환되어야 함)
            call_args = mock_session.post.call_args
            assert "/api/os-1/hw1/202012345/main@src@test.c/" in call_args[0][0]
            assert call_args[1]["json"] == {"bytes": 1024}

    @pytest.mark.asyncio
    async def test_register_snapshot_api_error(self, sender, sample_source_file_info):
        """API 요청 실패 테스트 (4xx/5xx 응답)"""
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.text = AsyncMock(return_value='{"error": "Not Found"}')
        
        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            
            result = await sender.register_snapshot(sample_source_file_info, 1024)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_register_snapshot_client_error(self, sender, sample_source_file_info):
        """aiohttp.ClientError 발생 테스트"""
        mock_session = AsyncMock()
        mock_session.post.side_effect = aiohttp.ClientError("Connection error")
        
        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            
            result = await sender.register_snapshot(sample_source_file_info, 1024)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_register_snapshot_unexpected_error(self, sender, sample_source_file_info):
        """예상치 못한 예외 발생 테스트"""
        mock_session = AsyncMock()
        mock_session.post.side_effect = Exception("Unexpected error")
        
        with patch('aiohttp.ClientSession') as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            
            result = await sender.register_snapshot(sample_source_file_info, 1024)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_register_snapshot_with_various_student_ids(self, sender):
        """다양한 student_id 형식 테스트 (모든 형식이 허용됨)"""
        test_cases = [
            "202012345",  # 일반적인 숫자
            "abc123",     # 숫자가 아닌 값도 허용 (백엔드에서 처리)
            "12.34",      # 소수점 포함
            "123abc",     # 혼합
        ]
        
        for student_id in test_cases:
            source_file_info = SourceFileInfo(
                class_div="os-1",
                hw_name="hw1", 
                student_id=student_id,
                filename="test.c",
                target_file_path=Path("/test/path/test.c")
            )
            
            mock_session_context, mock_session = self._create_mock_session()
            
            with patch('aiohttp.ClientSession', return_value=mock_session_context):
                result = await sender.register_snapshot(source_file_info, 1024)
                # 클라이언트는 모든 student_id 형식을 허용하고, 백엔드가 검증함
                assert result is True

    @pytest.mark.asyncio
    async def test_register_snapshot_url_encoding(self, sender):
        """특수 문자가 포함된 파일명 처리 테스트"""
        special_source_file_info = SourceFileInfo(
            class_div="os-1",
            hw_name="hw1",
            student_id="202012345",
            filename="file@with@special.c",
            target_file_path=Path("/test/path/file.c")
        )
        
        mock_session_context, mock_session = self._create_mock_session()
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await sender.register_snapshot(special_source_file_info, 512)
            
            assert result is True
            
            # URL에 파일명이 올바르게 포함되는지 확인
            call_args = mock_session.post.call_args
            assert "file@with@special.c" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_register_snapshot_zero_file_size(self, sender, sample_source_file_info):
        """파일 크기가 0인 경우 테스트 (삭제 이벤트)"""
        mock_session_context, mock_session = self._create_mock_session()
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await sender.register_snapshot(sample_source_file_info, 0)
            
            assert result is True
            
            # 0 바이트가 올바르게 전송되는지 확인
            call_args = mock_session.post.call_args
            assert call_args[1]["json"] == {"bytes": 0}

    @pytest.mark.parametrize("student_id,expected_url_part", [
        ("202012345", "202012345"),
        ("123456789", "123456789"), 
        ("000012345", "000012345"),  # 문자열 그대로 유지
        ("0", "0"),
    ])
    @pytest.mark.asyncio
    async def test_student_id_in_url(self, sender, student_id, expected_url_part):
        """student_id가 URL에 문자열 그대로 포함되는지 테스트"""
        source_file_info = SourceFileInfo(
            class_div="os-1",
            hw_name="hw1",
            student_id=student_id,
            filename="test.c",
            target_file_path=Path("/test/path/test.c")
        )
        
        mock_session_context, mock_session = self._create_mock_session()
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await sender.register_snapshot(source_file_info, 1024)
            
            assert result is True
            
            # URL에 원본 student_id가 그대로 포함되는지 확인
            call_args = mock_session.post.call_args
            assert f"/api/os-1/hw1/{expected_url_part}/test.c/" in call_args[0][0]

    @patch('app.sender.datetime')
    @pytest.mark.asyncio
    async def test_timestamp_generation(self, mock_datetime, sender, sample_source_file_info):
        """타임스탬프 생성 테스트"""
        # 고정된 시간 설정
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20240320_153000"
        mock_datetime.now.return_value = mock_now
        
        mock_session_context, mock_session = self._create_mock_session()
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await sender.register_snapshot(sample_source_file_info, 1024)
            
            assert result is True
            
            # 타임스탬프가 URL에 포함되는지 확인
            call_args = mock_session.post.call_args
            assert "20240320_153000" in call_args[0][0]
            
            # strftime이 올바른 형식으로 호출되는지 확인
            mock_now.strftime.assert_called_with("%Y%m%d_%H%M%S")