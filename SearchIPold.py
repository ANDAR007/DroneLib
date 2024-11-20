import subprocess
import threading


def ping(ip, results, stop_event):
    """
    Пингует указанный IP-адрес и добавляет его в список results, если пинг успешен.

    Параметры:
    - ip: строка, содержащая IP-адрес для проверки.
    - results: список, куда добавляются IP-адреса, которые успешно ответили на пинг.
    - stop_event: событие для остановки пингов после нахождения нужного количества дронов.
    """
    # Если уже нашли достаточно дронов, не проверяем дальше
    if stop_event.is_set():
        return

    response = subprocess.run(
        f"ping -n 1 -w 500 {ip}",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True
    )
    if response.returncode == 0:  # Если пинг успешен
        results.append(ip)
        # Если достигли необходимого числа дронов, устанавливаем событие для остановки
        if len(results) >= num_drones:
            stop_event.set()


def find_connected_drones(num_drones, subnet="192.168.137"):
    """
    Находит подключённые дроны в указанной подсети.

    Параметры:
    - num_drones: максимальное количество дронов для поиска.
    - subnet: подсеть, в которой ведётся поиск (по умолчанию "192.168.137").

    Возвращает:
    - Список IP-адресов найденных дронов.
    """
    connected_drones = []  # Список для хранения IP-адресов подключённых дронов
    threads = []  # Список потоков
    stop_event = threading.Event()  # Событие для остановки пингов

    for i in range(2, 255):  # Перебираем IP-адреса в подсети
        ip = f"{subnet}.{i}"
        thread = threading.Thread(target=ping, args=(ip, connected_drones, stop_event))
        threads.append(thread)
        thread.start()

        # Если уже нашли нужное количество дронов, не запускаем новые потоки
        if stop_event.is_set():
            break

    # Дожидаемся завершения всех потоков
    for thread in threads:
        thread.join()

    return connected_drones


# Использование функции
num_drones = 1  # Количество дронов, которые нужно найти
drones = find_connected_drones(num_drones)
print("Подключенные дроны:", drones)
