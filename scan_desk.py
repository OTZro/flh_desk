"""
BLE 掃描程式 - 用來掃描升降桌的藍牙資訊
"""
import asyncio
from bleak import BleakScanner, BleakClient


async def scan_devices():
    """掃描附近的 BLE 設備"""
    print("開始掃描 BLE 設備...\n")
    devices = await BleakScanner.discover(timeout=10.0)

    print(f"找到 {len(devices)} 個設備：\n")
    for i, device in enumerate(devices, 1):
        print(f"{i}. 名稱: {device.name or '未命名'}")
        print(f"   地址: {device.address}")
        print(f"   RSSI: {device.rssi} dBm")
        print()

    return devices


async def inspect_device(address):
    """詳細檢查指定設備的服務和特徵"""
    print(f"\n正在連接到 {address}...\n")

    try:
        async with BleakClient(address, timeout=15.0) as client:
            print(f"✓ 已連接到 {address}\n")

            # 獲取所有服務
            services = client.services

            print("=" * 60)
            print("設備服務和特徵：")
            print("=" * 60)

            for service in services:
                print(f"\n📦 服務: {service.uuid}")
                print(f"   描述: {service.description}")

                # 獲取服務下的所有特徵
                for char in service.characteristics:
                    print(f"\n   📝 特徵: {char.uuid}")
                    print(f"      描述: {char.description}")
                    print(f"      屬性: {char.properties}")

                    # 如果可以讀取，嘗試讀取值
                    if "read" in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            print(f"      當前值: {value.hex()} ({value})")
                        except Exception as e:
                            print(f"      讀取失敗: {e}")

                    # 列出描述符
                    for descriptor in char.descriptors:
                        print(f"         🔖 描述符: {descriptor.uuid}")

            print("\n" + "=" * 60)

    except Exception as e:
        print(f"❌ 連接失敗: {e}")


async def main():
    """主程式"""
    print("=" * 60)
    print("升降桌 BLE 掃描工具")
    print("=" * 60)

    # 第一步：掃描設備
    devices = await scan_devices()

    if not devices:
        print("沒有找到任何設備，請確保：")
        print("1. 升降桌已開機")
        print("2. 藍牙已啟用")
        print("3. 設備在附近")
        return

    # 讓用戶選擇要檢查的設備
    print("\n請輸入要檢查的設備編號（或輸入設備名稱關鍵字）：")
    choice = input("> ").strip()

    target_device = None

    # 如果輸入是數字
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(devices):
            target_device = devices[idx]
    else:
        # 如果輸入是名稱關鍵字，搜尋匹配的設備
        for device in devices:
            if device.name and choice.lower() in device.name.lower():
                target_device = device
                break

    if target_device:
        await inspect_device(target_device.address)
    else:
        print("❌ 無效的選擇")


if __name__ == "__main__":
    asyncio.run(main())