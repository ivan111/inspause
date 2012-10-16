/* based on http://www.badlogicgames.com/wordpress/?p=231 */

#include "mad.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

#define SHRT_MAX (32767) 
#define INPUT_BUFFER_SIZE	(5*8192)
#define OUTPUT_BUFFER_SIZE	8192 /* Must be an integer multiple of 4. */
#define TRUE (1)

/**
 * Struct holding the pointer to a wave file.
 */
typedef struct
{
    int size;
    FILE* file;
    struct mad_stream stream;
    struct mad_frame frame;
    struct mad_synth synth;
    mad_timer_t timer;
    int leftSamples;
    int offset;
    unsigned char inputBuffer[INPUT_BUFFER_SIZE];
} MP3FileHandle;

/** static MP3FileHandle array **/
static MP3FileHandle* handles[100];

/**
 * Seeks a free handle in the handles array and returns its index or -1 if no handle could be found
 */
static int findFreeHandle()
{
    int i;

    for (i = 0; i < 100; i++) {
        if (handles[i] == NULL)
            return i;
    }

    return -1;
}

static void closeHandle(MP3FileHandle* handle)
{
    fclose(handle->file);
    mad_synth_finish(&handle->synth);
    mad_frame_finish(&handle->frame);
    mad_stream_finish(&handle->stream);
    free(handle);
}

static signed short fixedToShort(mad_fixed_t Fixed)
{
    if(Fixed >= MAD_F_ONE)
        return SHRT_MAX;
    if(Fixed <= -MAD_F_ONE)
        return -SHRT_MAX;

    Fixed = Fixed >> (MAD_F_FRACBITS - 15);
    return (signed short) Fixed;
}

int openFile(const char* fileName)
{
    int index = findFreeHandle();
    FILE* fileHandle;
	MP3FileHandle* mp3Handle;

    if (index == -1) {
        return -1;
    }

	fileHandle = fopen(fileName, "rb");

    if (fileHandle == 0) {
        return -1;
    }

    mp3Handle = (MP3FileHandle *) malloc(sizeof(MP3FileHandle));
    mp3Handle->file = fileHandle;
    fseek(fileHandle, 0, SEEK_END);
    mp3Handle->size = ftell(fileHandle);
    rewind(fileHandle);

    mad_stream_init(&mp3Handle->stream);
    mad_frame_init(&mp3Handle->frame);
    mad_synth_init(&mp3Handle->synth);
    mad_timer_reset(&mp3Handle->timer);

    handles[index] = mp3Handle;
    return index;
}

void closeFile(int handle)
{
    if (handles[handle] != NULL) {
        closeHandle(handles[handle]);
        handles[handle] = NULL;
    }
}

unsigned int getSamplerate(int handle)
{
	unsigned int samplerate = 0;
	MP3FileHandle* mp3;

	if (handles[handle] != NULL) {
	    mp3 = handles[handle];
		samplerate = mp3->frame.header.samplerate;
	}

	return samplerate;
}

int getNumChannels(int handle)
{
	int ch = 2;
	MP3FileHandle* mp3;

	if (handles[handle] != NULL) {
	    mp3 = handles[handle];
		ch = MAD_NCHANNELS(&mp3->frame.header);
	}

	return ch;
}

static int readNextFrame(MP3FileHandle* mp3)
{
    int i;
	int inputBufferSize;
	int leftOver;
	int readBytes;

    do {
        if (mp3->stream.buffer == 0 || mp3->stream.error == MAD_ERROR_BUFLEN) {
            inputBufferSize = 0;
            if (mp3->stream.next_frame != 0) {
                leftOver = mp3->stream.bufend - mp3->stream.next_frame;
				for (i = 0; i < leftOver; i++) {
                    mp3->inputBuffer[i] = mp3->stream.next_frame[i];
				}
                readBytes = fread(mp3->inputBuffer + leftOver, 1, INPUT_BUFFER_SIZE - leftOver, mp3->file);
                if (readBytes == 0)
                    return 0;
                inputBufferSize = leftOver + readBytes;
            } else {
                int readBytes = fread(mp3->inputBuffer, 1, INPUT_BUFFER_SIZE, mp3->file);
                if (readBytes == 0)
                    return 0;
                inputBufferSize = readBytes;
            }

            mad_stream_buffer(&mp3->stream, mp3->inputBuffer, inputBufferSize);
            mp3->stream.error = MAD_ERROR_NONE;
        }

        if (mad_frame_decode(&mp3->frame, &mp3->stream)) {
            if (mp3->stream.error == MAD_ERROR_BUFLEN ||(MAD_RECOVERABLE(mp3->stream.error)))
                continue;
            else
                return 0;
        } else
            break;
    } while (TRUE);

    mad_timer_add(&mp3->timer, mp3->frame.header.duration);
    mad_synth_frame(&mp3->synth, &mp3->frame);
    mp3->leftSamples = mp3->synth.pcm.length;
    mp3->offset = 0;

    return -1;
}

int readFrames(int handle, short* target, int size)
{
    MP3FileHandle* mp3 = handles[handle];

    int idx = 0;
    while (idx < size) {
        if (mp3->leftSamples > 0) {
            for ( ; idx < size && mp3->offset < mp3->synth.pcm.length; mp3->leftSamples--, mp3->offset++) {
                int value = fixedToShort(mp3->synth.pcm.samples[0][mp3->offset]);
                target[idx++] = value;

                if (MAD_NCHANNELS(&mp3->frame.header) == 2) {
                    value = fixedToShort(mp3->synth.pcm.samples[1][mp3->offset]);
					target[idx++] = value;
                }
            }
        } else {
            int result = readNextFrame(mp3);
            if (result == 0)
                return 0;
        }
    }
    if (idx > size)
        return 0;

    return size;
}

int readFramesMono(int handle, short* target, int size)
{
    MP3FileHandle* mp3 = handles[handle];

    int idx = 0;
    while (idx < size) {
        if (mp3->leftSamples > 0) {
            for ( ; idx < size && mp3->offset < mp3->synth.pcm.length; mp3->leftSamples--, mp3->offset++) {
                int value = fixedToShort(mp3->synth.pcm.samples[0][mp3->offset]);

                if (MAD_NCHANNELS(&mp3->frame.header) == 2) {
                    value += fixedToShort(mp3->synth.pcm.samples[1][mp3->offset]);
                }

                target[idx++] = value;
            }
        } else {
            int result = readNextFrame(mp3);
            if (result == 0)
                return 0;
        }
    }
    if (idx > size)
        return 0;

    return size;
}
