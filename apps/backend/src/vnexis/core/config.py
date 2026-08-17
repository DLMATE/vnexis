"""
애플리케이션 인프라 설정.
- 환경 변수에서 설정을 읽어 애플리케이션에 제공
- 데이터베이스 접속 URL 등 인프라 관심사만 담는다
"""

import os


class Config:
    """애플리케이션 설정."""

    # 기본값: 실행 위치 기준 SQLite 파일
    DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./vnexis.db"

    @classmethod
    def get_database_url(cls) -> str:
        """데이터베이스 접속 URL을 가져온다.

        Returns:
            VNEXIS_DATABASE_URL 환경 변수 값. 없으면 기본 SQLite URL.
        """
        return os.getenv("VNEXIS_DATABASE_URL", cls.DEFAULT_DATABASE_URL)
