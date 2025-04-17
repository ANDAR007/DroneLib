import socket
import struct
import base64
import cv2
import numpy as np
from typing import Optional

def receive_all(sock: socket.socket, count: int) -> bytes:
    """
    Получает точно count байт из сокета.

    :param sock: Сокет для чтения данных.
    :param count: Количество байт, которые необходимо получить.
    :return: Полученные данные в виде байтов.
    """
    buf = b""
    while len(buf) < count:
        new_buf = sock.recv(count - len(buf))
        if not new_buf:
            break
        buf += new_buf
    return buf

def main() -> None:
    """
    Основная функция клиентской стороны для получения и отображения видеопотока.
    """
    host: str = '192.168.137.250'  # IP-адрес сервера видеопотока (Tello)
    port: int = 9999          # Используется для управления, но видеопоток Tello шлёт на 11111

    # Попытка открыть видеопоток. Обратите внимание на использование "udp://@0.0.0.0:11111"
    cap: cv2.VideoCapture = cv2.VideoCapture("udp://@0.0.0.0:11111")
    if not cap.isOpened():
        print("Не удалось открыть видеопоток!")
        return

    while True:
        ret, frame = cap.read()
        if ret:
            cv2.imshow("Видеопоток с Tello", frame)
            # Нажмите 'q' для выхода
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            print("Ошибка получения кадра!")
            break
#бахнуть слушанье команд с клавиатуры. Можно забиндить на стрелки к примеру
    cap.release()
    cv2.destroyAllWindows()
    print("Соединение закрыто.")

if __name__ == "__main__":
    main()
