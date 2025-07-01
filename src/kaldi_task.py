from vosk import Model, KaldiRecognizer
from av.audio.resampler import AudioResampler
import os
from pathlib import Path
import asyncio
from loguru import logger

import concurrent.futures

vosk_dump_file = None

model = Model(lang='en-us')
#Manage a pool of threads to process audio data
pool = concurrent.futures.ThreadPoolExecutor((os.cpu_count() or 1))
dump_fd = None if vosk_dump_file is None else open(vosk_dump_file, "wb")

def process_chunk(recognizer, message):
    try:
        res = recognizer.AcceptWaveform(message)
        logger.debug(f"Recognizer returned: {res}")
    except Exception :
        result = None
    else:
        if res > 0:
            result = recognizer.Result()
        else:
            result = recognizer.PartialResult()
            #logger.debug(f"Partial result: {result}")
    return result

class KaldiTask:
    #Wrapper for peer connection
    def __init__(self, peer_connection):
        self.__resampler = AudioResampler(format='s16', layout='mono', rate=48000)
        self.__pc = peer_connection
        self.__audio_task = None
        self.__track = None
        self.__channel = None # data channel
        self.__recognizer = KaldiRecognizer(model, 48000) # default us-en

    async def set_audio_strack(self, track):
        self.__track = track
    
    async def set_text_channel(self,channel):
        self.__channel = channel
        
    async def start(self):
        logger.info("Starting KaldiTask")
        #run in background without blocking the main event loop
        self.__audio_task = asyncio.create_task(self.__run_audio_xfer())

    async def __run_audio_xfer(self):
        #get current async loop to run heavy task in a separate thread without blocking async flow
        loop = asyncio.get_running_loop()

        max_frames = 50
        frames = []
        try :
            while True:
                frame = await self.__track.recv()
                logger.debug(f"Received audio frame: {frame}")
                frames.append(frame)

                if len(frames) < max_frames:
                    continue
                
                #process frames
                dataframes = bytearray(b'')
                for fr in frames:
                    for rfr in self.__resampler.resample(fr):
                        plane_bytes = bytes(rfr.planes[0])
                        dataframes += plane_bytes[:rfr.samples * 2]
                        logger.debug(f"Processed frame: {rfr.samples} samples, {len(plane_bytes)} bytes") 
                frames.clear()
                
                if dump_fd is not None:
                    dump_fd.write(bytes(dataframes))
                #process in a separate thread to avoid blocking the event loop
                result = await loop.run_in_executor(pool, process_chunk, self.__recognizer, bytes(dataframes))
                if result is not None:
                    logger.info(f"Kaldi recognizer result: {result}")
                    if self.__channel is not None and self.__channel.readyState == "open":
                        logger.debug(f"Sending result to data channel: {result}")
                        self.__channel.send(result)
                    else:
                        logger.warning("Data channel not open, cannot send result")
                else:
                    logger.error("Kaldi recognizer returned None, check your audio input or model")
        except Exception as e:
            logger.error(f"Error in KaldiTask audio processing: {e}")
                