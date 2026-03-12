from app.models.allergy import Allergy
from app.models.chronic_disease import ChronicDisease
from app.models.user import User


class UserRepository:
    """
    User 모델에 대한 데이터베이스 접근 및 CRUD 연산을 담당하는 레포지토리 클래스입니다.
    """

    def __init__(self):
        self._model = User
        self._allergy = Allergy
        self._chronic_disease = ChronicDisease

    # 회원가입
    async def create_user(self, data: dict) -> User:
        """
        새로운 사용자 레코드를 데이터베이스에 생성합니다.

        Args:
            data (dict): 저장할 사용자 정보 딕셔너리

        Returns:
            User: 생성된 사용자 객체
        """

        # dict 언패킹(**)을 사용하여 간단하게 생성
        user: User = await self._model.create(**data)  # type: ignore[assignment]

        return user

    # 이메일 찾기
    async def find_id_by_info(self, name: str, phone_number: str) -> User | None:
        """
        성명과 휴대폰 번호를 대조하여 일치하는 사용자를 찾습니다.

        Args:
            name (str): 이름
            phone_number (str): 휴대폰 번호

        Returns:
            User | None: 일치하는 사용자 정보 또는 없음
        """
        user: User | None = await self._model.get_or_none(name=name, phone_number=phone_number)  # type: ignore[assignment]
        return user

    async def get_by_name_and_phone(self, name: str, phone_number: str) -> User | None:
        """
        성명과 휴대폰 번호를 대조하여 일치하는 사용자를 찾습니다.

        Args:
            name (str): 이름
            phone_number (str): 휴대폰 번호

        Returns:
            User | None: 일치하는 사용자 정보 또는 없음
        """
        user: User | None = await self._model.get_or_none(name=name, phone_number=phone_number)  # type: ignore[assignment]
        return user

    # 비밀번호 찾기
    async def get_user_for_reset(self, id: str, name: str, phone_number: str) -> User | None:
        """
        비밀번호 재설정을 위해 입력된 사용자 정보가 모두 일치하는지 확인합니다.

        Args:
            id (str): 사용자 아이디
            name (str): 이름
            phone_number (str): 휴대폰 번호

        Returns:
            User | None: 모든 정보가 일치하는 사용자 객체 또는 없음
        """
        user: User | None = await self._model.get_or_none(id=id, name=name, phone_number=phone_number)  # type: ignore[assignment]
        return user

    # 이메일 중복 확인
    async def get_by_id(self, id: str) -> User | None:
        """
        고유한 아이디(이메일)를 기준으로 한 명의 사용자를 조회합니다.

        Args:
            id (str): 조회할 아이디

        Returns:
            User | None: 사용자 객체 또는 없음
        """
        user = await self._model.filter(id=id).prefetch_related("allergies", "chronic_diseases").first()
        return user  # type: ignore[no-any-return]

    # 전화번호 중복 확인
    async def exists_by_phone_number(self, phone_number: str) -> bool:
        """
        지정된 휴대폰 번호가 이미 존재하는지 여부를 확인합니다.

        Args:
            phone_number (str): 확인할 휴대폰 번호

        Returns:
            bool: 존재 여부
        """
        result: bool = await self._model.filter(phone_number=phone_number).exists()  # type: ignore[assignment]
        return result

    # 주민번호 중복 확인
    async def exists_by_resident_registration_number(self, resident_registration_number: str) -> bool:
        """
        지정된 주민등록번호가 이미 등록되어 있는지 여부를 확인합니다.

        Args:
            resident_registration_number (str): 확인할 주민등록번호

        Returns:
            bool: 존재 여부
        """
        result: bool = await self._model.filter(resident_registration_number=resident_registration_number).exists()  # type: ignore[assignment]
        return result
