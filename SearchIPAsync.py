import asyncio


async def ping(ip):
    """
    Асинхронно пингует указанный IP-адрес.

    Параметры:
    - ip: строка, содержащая IP-адрес для проверки.

    Возвращает:
    - True, если пинг успешен; False в противном случае.
    """
    proc = await asyncio.create_subprocess_shell(
        f"ping -n 1 -w 500 {ip}",
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL
    )
    await proc.communicate()  # Ожидаем завершения команды
    return proc.returncode == 0  # Возвращаем True, если пинг успешен


async def find_connected_drones(num_drones, subnet="192.168.137"):
    """
    Асинхронно находит подключённые дроны в указанной подсети.

    Параметры:
    - num_drones: максимальное количество дронов для поиска.
    - subnet: подсеть, в которой ведётся поиск (по умолчанию "192.168.137").

    Возвращает:
    - Список IP-адресов найденных дронов.
    """
    connected_drones = []  # Список для хранения IP-адресов подключённых дронов
    tasks = []  # Список задач asyncio

    # Перебираем IP-адреса в указанной подсети
    for i in range(2, 255):
        ip = f"{subnet}.{i}"
        tasks.append(ping(ip))

    # Ожидаем завершения всех задач
    results = await asyncio.gather(*tasks)

    # Собираем все успешные пинги в список
    for i, success in enumerate(results, start=2):
        if success:
            connected_drones.append(f"{subnet}.{i}")
        if len(connected_drones) >= num_drones:  # Проверяем, достигли ли нужного количества дронов
            break

    return connected_drones


# Основная точка входа
if __name__ == "__main__":
    num_drones = 5  # Количество дронов, которые нужно найти
    drones = asyncio.run(find_connected_drones(num_drones))
    print("Подключенные дроны:", drones)
