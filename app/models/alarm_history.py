from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from tortoise import fields, models

if TYPE_CHECKING:
    from app.models.alarm import Alarm


class AlarmHistory(models.Model):
    """
    알람 발송 내역과 사용자의 확인 여부를 기록하는 모델입니다.
    Alarm(MED/혈압/혈당) 모두의 발송 이력을 통합 관리합니다.

    - MED 타입: is_confirmed = 복약 완료 체크 여부
    - 혈압/혈당 타입: is_confirmed = 측정 완료 체크 여부
    - snoozed_until: 사용자가 "10분 후 다시 알림"을 눌렀을 때 재노출 예정 시각
    - snooze_count: 사용자가 해당 알람을 몇 번 미뤘는지 카운트
    """

    id = fields.IntField(pk=True)
    sent_at = fields.DatetimeField(auto_now_add=True)  # 알람 발송 시각 (UTC)
    delivered_at = fields.DatetimeField(null=True)  # 기기 도착 시각 (UTC)
    read_at = fields.DatetimeField(null=True)  # 사용자 확인 시각 (UTC)
    is_confirmed = fields.BooleanField(default=False)  # 확인(복약/측정 완료) 여부

    # 기능 A: 알람 미루기(10분 후) 대응용
    snoozed_until = fields.DatetimeField(null=True)  # 다시 보여줄 예정 시각 (UTC)
    snooze_count = fields.IntField(default=0)  # 미루기 횟수

    alarm: fields.ForeignKeyRelation["Alarm"] = fields.ForeignKeyField(
        "models.Alarm",
        related_name="histories",
    )

    @property
    def sent_at_kst(self):
        """발송 시각을 KST로 변환"""
        return self.sent_at.astimezone(ZoneInfo("Asia/Seoul"))

    @property
    def delivered_at_kst(self):
        """도착 시각을 KST로 변환"""
        return self.delivered_at.astimezone(ZoneInfo("Asia/Seoul")) if self.delivered_at else None

    @property
    def read_at_kst(self):
        """확인 시각을 KST로 변환"""
        return self.read_at.astimezone(ZoneInfo("Asia/Seoul")) if self.read_at else None

    @property
    def snoozed_until_kst(self):
        """미루기 재알림 시각을 KST로 변환"""
        return self.snoozed_until.astimezone(ZoneInfo("Asia/Seoul")) if self.snoozed_until else None

    class Meta:
        table = "alarm_history"
