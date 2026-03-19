import logging
import os
import subprocess
import sys
import threading
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
drug_router = APIRouter(prefix="/drugs", tags=["Drugs"])


def _cleanup_old_logs(log_dir: str, keep_days: int = 7):
    """drug_sync_*.log 파일 중 keep_days일보다 오래된 파일을 삭제합니다."""

    cutoff = date.today() - timedelta(days=keep_days)
    for filename in os.listdir(log_dir):
        if filename.startswith("drug_sync_") and filename.endswith(".log"):
            date_str = filename[len("drug_sync_") : -len(".log")]  # 'YYYYMMDD'
            try:
                file_date = datetime.strptime(date_str, "%Y%m%d").date()
                if file_date < cutoff:
                    os.remove(os.path.join(log_dir, filename))
                    logger.info("Removed old drug sync log: %s", filename)
            except ValueError:
                pass  # 파일명 형식이 다르면 무시


def _monitor_sync_process(proc: subprocess.Popen, log_path: str):
    """subprocess 종료를 기다려 FastAPI 로거에 완료/에러 상태만 기록합니다."""
    proc.wait()
    if proc.returncode == 0:
        logger.info("Drug sync process finished successfully. (log: %s)", log_path)
    else:
        logger.error("Drug sync process exited with code %d. See %s for details.", proc.returncode, log_path)


@drug_router.get("/sync-background")
async def sync_drug_data_background():
    """
    별도의 프로세스(.py)를 실행하여 백그라운드에서 동기화 및 LLM 보충을 전체 수행합니다.
    FastAPI 로그에는 시작/종료/에러 3가지 상태만 기록됩니다.
    세부 로그는 logs/drug_sync.log 에서 확인하세요.
    """
    try:
        script_path = os.path.join(os.getcwd(), "scripts", "standalone_drug_sync.py")
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"Sync script not found at {script_path}")

        # 세부 로그를 날짜별 파일로 분리 (매일 자동 초기화)
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        _cleanup_old_logs(log_dir)  # 7일 초과 로그 자동 삭제
        log_path = os.path.join(log_dir, f"drug_sync_{date.today().strftime('%Y%m%d')}.log")

        log_file = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            [sys.executable, script_path],
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL,
            cwd=os.getcwd(),
            env={**os.environ, "PYTHONPATH": os.getcwd()},
        )
        log_file.close()  # Python 쪽 핸들은 닫아도 subprocess는 독립 fd 유지

        logger.info("Drug sync process started. (PID: %d, log: %s)", proc.pid, log_path)

        # 완료/에러 감지를 위한 daemon 스레드 (FastAPI 이벤트 루프 차단 없음)
        threading.Thread(
            target=_monitor_sync_process,
            args=(proc, log_path),
            daemon=True,
        ).start()

        return {
            "status": "started",
            "pid": proc.pid,
            "message": "동기화 및 LLM 보충 작업이 백그라운드에서 시작되었습니다.",
            "log_file": log_path,
        }
    except Exception as e:
        logger.error("Failed to start drug sync process: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Failed to start background process: {str(e)}") from e
