import asyncio
import websockets
import logging
import json
import cv2
import time
import argparse
from subprocess import Popen


parser = argparse.ArgumentParser(
                    prog='Daisy-Chain Client',
                    description='Daisy-Chain RTSP yayın sistemi.'
                )
parser.add_argument('--ip', dest='mainframe', help='Ana websocket sunucusunun ip adresi.', default='127.0.0.1')
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s - %(levelname)s %(message)s', level=logging.INFO)
logger = logging.getLogger('daisychain')


async def client():
    async with websockets.connect(f"ws://{args.mainframe}:8765") as websocket:
        try:
            response = await websocket.recv()
            response = json.loads(response)
            if response["streamer"]:
                mediamtx_server = Popen(['mediamtx/mediamtx.exe', 'mediamtx/mediamtx.yml']) # Run mediamtx
                time.sleep(1)
                ffmpeg = Popen(["ffmpeg/ffmpeg.exe", "-re", "-i", f"rtsp://{response['get_stream_from']}:8554/1", "-preset", "veryfast", "-tune", "zerolatency", "-f", "rtsp", "rtsp://localhost:8554/1"])
                logger.info("Starting RSTP server...")

            cap = cv2.VideoCapture(f"rtsp://{response['get_stream_from']}:8554/1")
            if cap.isOpened():
                cv2.namedWindow("RTSP Stream", cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty("RTSP Stream", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

                while cap.isOpened():
                    ret, frame = cap.read()

                    cv2.imshow("RTSP Stream", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                
                cap.release()
                cv2.destroyAllWindows()
            else:
                logger.error("Yayın başlatılmamış, sorumluyla iletişime geçin.")

        except KeyboardInterrupt:
            logger.info("İstemci kapatıldı.")
        except json.JSONDecodeError:
            logger.error("Unsupported response.")


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(client())
    asyncio.get_event_loop().run_forever()