"""
Yandex Cloud — резервирование публичного IP с нужными первыми октетами.

Запуск: python3 reserve_ip.py
После открытия браузера залогинься вручную, затем нажми "Resume" в Playwright Inspector.
"""

import re
import time
from playwright.sync_api import sync_playwright

FOLDER_URL = "https://console.yandex.cloud/folders/b1guqmcuugq310ln9613/vpc/addresses"
ZONES = ["ru-central1-a", "ru-central1-b", "ru-central1-d"]
TARGET_PREFIXES = ("51.250.", "84.201.")
MAX_ATTEMPTS = 200

IP_XPATH = "/html/body/div[1]/div[1]/div/div[2]/div/div[1]/div[2]/div/div[3]/div[1]/table/tbody/tr[{row}]/td[3]/div/div[1]/div/span"
MENU_XPATH = "/html/body/div[1]/div[1]/div/div[2]/div/div[1]/div[2]/div/div[3]/div[1]/table/tbody/tr[{row}]/td[13]/div"


def wait(page, seconds=5):
    page.wait_for_load_state("networkidle", timeout=60000)
    time.sleep(seconds)


def get_table_ips(page) -> list[str]:
    ips = []
    for row in range(1, 10):
        try:
            el = page.locator(f"xpath={IP_XPATH.format(row=row)}")
            if el.count() == 0:
                break
            text = el.inner_text(timeout=3000)
            if re.match(r"\d+\.\d+\.\d+\.\d+", text.strip()):
                ips.append(text.strip())
            else:
                break
        except Exception:
            break
    return ips


def reserve_ip(page, zone: str):
    reserve_btn = page.get_by_role("button", name="Зарезервировать публичный IP-адрес").first
    reserve_btn.wait_for(state="visible", timeout=30000)
    reserve_btn.click()
    page.wait_for_timeout(3000)

    page.locator("div.g-select.form-field-select-next").click()
    page.wait_for_timeout(2000)

    page.get_by_title(zone, exact=True).click()
    page.wait_for_timeout(2000)

    page.locator("button:has-text('Зарезервировать')").last.click()
    page.wait_for_timeout(8000)
    wait(page)


def delete_row(page, row: int):
    page.locator(f"xpath={MENU_XPATH.format(row=row)}").click()
    page.wait_for_timeout(2000)

    page.get_by_text("Удалить", exact=True).first.click()
    page.wait_for_timeout(2000)

    page.get_by_text("Удалить", exact=True).last.click()
    page.wait_for_timeout(5000)
    wait(page)


def delete_all_ips(page):
    while True:
        ips = get_table_ips(page)
        if not ips:
            break
        delete_row(page, 1)


def main():
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir="./browser_data",
            headless=False,
            viewport={"width": 1400, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        page.goto(FOLDER_URL)
        print("Залогинься и нажми Resume в Playwright Inspector.")
        page.pause()

        wait(page)

        zone_idx = 0
        try:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                zone = ZONES[zone_idx % len(ZONES)]
                zone_idx += 1

                reserve_ip(page, zone)

                ips = get_table_ips(page)
                print(f"[{attempt}] {zone}: {ips}")

                found = None
                for ip in ips:
                    if ip.startswith(TARGET_PREFIXES):
                        found = ip
                        break

                if found:
                    print(f"\nУСПЕХ: {found}")
                    page.pause()
                    break

                if len(ips) >= 2:
                    delete_all_ips(page)

            else:
                print(f"Не нашёл за {MAX_ATTEMPTS} попыток.")
        except Exception as e:
            print(f"ОШИБКА: {e}")
            page.pause()

        context.close()


if __name__ == "__main__":
    main()
