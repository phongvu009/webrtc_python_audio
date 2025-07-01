from faster_whisper import WhisperModel
from av.audio.resampler import AudioResampler
import numpy as np
import os
import asyncio
from loguru import logger
import concurrent.futures

WHISPER_MODEL_SIZE = "small"
model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))

def process_chunk_whisper(audio_bytes):
    audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    segments, info = model.transcribe(audio_np, language="en", beam_size=1)
    result_text = " ".join([segment.text for segment in segments])
    logger.debug(f"Whisper result: {result_text}")
    return result_text

class KaldiTask:
    def __init__(self, peer_connection):
        self.__resampler = AudioResampler(format='s16', layout='mono', rate=16000)
        self.__pc = peer_connection
        self.__audio_task = None
        self.__recv_task = None
        self.__track = None
        self.__channel = None
        self._audio_queue = asyncio.Queue(maxsize=100)

    async def set_audio_strack(self, track):
        self.__track = track

    async def set_text_channel(self, channel):
        self.__channel = channel

    async def start(self):
        logger.info("Starting WhisperTask")
        self.__recv_task = asyncio.create_task(self._receive_audio())
        self.__audio_task = asyncio.create_task(self.__run_audio_xfer())

    async def _receive_audio(self):
        try:
            while True:
                frame = await self.__track.recv()
                await self._audio_queue.put(frame)
                logger.debug(f"Queued audio frame: {frame}")
        except Exception as e:
            logger.error(f"Error receiving audio: {e}")

    async def __run_audio_xfer(self):
        loop = asyncio.get_running_loop()
        max_frames = 50
        frames = []
        try:
            while True:
                frame = await self._audio_queue.get()
                logger.debug(f"Processing audio frame: {frame}")
                frames.append(frame)

                if len(frames) < max_frames:
                    continue

                dataframes = bytearray(b'')
                for fr in frames:
                    for rfr in self.__resampler.resample(fr):
                        plane_bytes = bytes(rfr.planes[0])
                        dataframes += plane_bytes[:rfr.samples * 2]
                        logger.debug(f"Processed frame: {rfr.samples} samples, {len(plane_bytes)} bytes")
                frames.clear()

                result = await loop.run_in_executor(pool, process_chunk_whisper, bytes(dataframes))
                if result:
                    logger.info(f"Whisper recognizer result: {result}")
                    if self.__channel is not None and self.__channel.readyState == "open":
                        logger.debug(f"Sending result to data channel: {result}")
                        self.__channel.send(result)
                    else:
                        logger.warning("Data channel not open, cannot send result")
                else:
                    logger.error("Whisper recognizer returned None or empty result")
        except Exception as e:
            logger.error(f"Error in WhisperTask audio processing: {e}")
