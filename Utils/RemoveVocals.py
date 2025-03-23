import multiprocessing

if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    from spleeter.separator import Separator
    separator = Separator('spleeter:2stems')
    separator.separate_to_file('/Users/nuthan/Music/Music/Media/Music/Various Artists/Muthu - (1995)/05 Okade Okadu.mp3', '/Users/nuthan/Music/Ringtones')
    print("Vocals removed and saved in the output directory.")

# from pydub import AudioSegment
# import numpy as np
#
#
# def remove_vocals(input_file, output_file):
#     # Load audio file
#     song = AudioSegment.from_file(input_file)
#
#     # Split stereo into two channels (left and right)
#     channels = song.split_to_mono()
#
#     # Get the left and right channels
#     left_channel = np.array(channels[0].get_array_of_samples())
#     right_channel = np.array(channels[1].get_array_of_samples())
#
#     # Subtract the right channel from the left channel
#     # This cancels out the common (center-panned) elements (usually vocals)
#     vocal_removed = left_channel - right_channel
#
#     # Convert the result back into an AudioSegment
#     vocal_removed = AudioSegment(
#         vocal_removed.tobytes(),
#         frame_rate=song.frame_rate,
#         sample_width=song.sample_width,
#         channels=1
#     )
#
#     # Export the result
#     vocal_removed.export(output_file, format="mp3")
#     print(f"Vocals removed and saved to {output_file}")
#
#
# # Example usage
# input_file = '/Users/nuthan/Music/Music/Media/Music/Various Artists/Muthu - (1995)/05 Okade Okadu.mp3'
# output_file = '/Users/nuthan/Music/Ringtones/Muthu.mp3'
# remove_vocals(input_file, output_file)
#
# import librosa
# import numpy as np
# import scipy.signal as signal
# import soundfile as sf
#
#
# def band_stop_filter(audio, sr, low_freq, high_freq, order=4):
#     """
#     Apply a band-stop filter to remove frequencies between low_freq and high_freq.
#     audio: Audio signal (numpy array)
#     sr: Sample rate
#     low_freq: Lower bound of the frequency to be removed
#     high_freq: Upper bound of the frequency to be removed
#     order: Order of the filter (higher order = sharper cut)
#     """
#     nyquist = 0.5 * sr
#     low = low_freq / nyquist
#     high = high_freq / nyquist
#
#     # Design a band-stop filter
#     b, a = signal.butter(order, [low, high], btype='bandstop')
#
#     # Apply the filter to the audio
#     filtered_audio = signal.filtfilt(b, a, audio)
#     return filtered_audio
#
#
# def remove_frequencies(input_file, output_file, low_freq=500, high_freq=2000):
#     # Load audio file
#     audio, sr = librosa.load(input_file, sr=None)
#
#     # Apply band-stop filter to remove the specified frequency range
#     filtered_audio = band_stop_filter(audio, sr, low_freq, high_freq)
#
#     # Save the filtered audio
#     sf.write(output_file, filtered_audio, sr)
#     print(f"Filtered audio saved to {output_file}")
#
#
# # Example usage
# input_file = '/Users/nuthan/Music/Music/Media/Music/A. R. Rahman/Jaane Tu... Ya Jaane Na/01 Kabhi Kabhi Aditi Zindagi.mp3'  # Replace with your input file path
# output_file = '/Users/nuthan/Music/Ringtones/JTYJN.mp3'  # Output file path
# remove_frequencies(input_file, output_file)
