"""
따릉이 실시간 대여정보 1회 수집 (GitHub Actions에서 10분마다 실행)
- 인증키는 GitHub Secrets의 SEOUL_API_KEY에서 읽음 (코드에 직접 쓰지 않음)
- data/YYYYMMDD/HHMM.csv.gz : 시각별 거치 현황 (대여소ID, 거치대수, 자전거수)
- data/stations/stations_YYYYMMDD.csv : 하루 한 번 대여소 이름·좌표
"""
import csv
import gzip
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

API_KEY = os.environ["SEOUL_API_KEY"]
URL = "http://openapi.seoul.go.kr:8088/{key}/json/bikeList/{s}/{e}/"
PAGE = 1000


def fetch():
    rows, s = [], 1
    while True:
        res = requests.get(URL.format(key=API_KEY, s=s, e=s + PAGE - 1), timeout=30)
        res.raise_for_status()
        data = res.json()
        if "rentBikeStatus" not in data:
            break
        page = data["rentBikeStatus"]["row"]
        rows.extend(page)
        if len(page) < PAGE:
            break
        s += PAGE
    return rows


def main():
    now = datetime.now(ZoneInfo("Asia/Seoul"))
    for attempt in range(3):
        try:
            rows = fetch()
            if rows:
                break
        except Exception as e:
            print(f"오류({attempt + 1}/3): {e}")
        time.sleep(20)
    else:
        sys.exit("3번 모두 실패")

    day_dir = os.path.join("data", f"{now:%Y%m%d}")
    os.makedirs(day_dir, exist_ok=True)
    path = os.path.join(day_dir, f"{now:%H%M}.csv.gz")
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")
    with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["collected_at", "stationId", "rackTotCnt", "parkingBikeTotCnt"])
        for r in rows:
            w.writerow([stamp, r["stationId"], r["rackTotCnt"], r["parkingBikeTotCnt"]])

    st_dir = os.path.join("data", "stations")
    os.makedirs(st_dir, exist_ok=True)
    st_path = os.path.join(st_dir, f"stations_{now:%Y%m%d}.csv")
    if not os.path.exists(st_path):
        with open(st_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["stationId", "stationName", "rackTotCnt", "stationLatitude", "stationLongitude"])
            for r in rows:
                w.writerow([r["stationId"], r["stationName"], r["rackTotCnt"],
                            r["stationLatitude"], r["stationLongitude"]])

    print(f"{stamp} {len(rows)}개 대여소 저장 → {path}")


if __name__ == "__main__":
    main()
