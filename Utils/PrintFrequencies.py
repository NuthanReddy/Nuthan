import librosa
import numpy as np
import matplotlib.pyplot as plt


def extract_frequencies(input_file, n_fft=2048, hop_length=512):
    # Load the audio file
    y, sr = librosa.load(input_file, sr=None)

    # Compute the Short-Time Fourier Transform (STFT)
    D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)

    # Convert amplitude to decibels for better visualization
    D_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    # Get the corresponding time and frequency axes
    times = librosa.times_like(D, hop_length=hop_length)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Print out the frequencies at each timestamp
    # print("Frequencies present at each timestamp:")
    # for t, time in enumerate(times):
    #     print(f"Timestamp: {time:.2f}s - Frequencies: {freqs[D[:, t].argsort()[-5:]]}")

    # Optionally plot the spectrogram (time vs. frequency)
    plt.figure(figsize=(10, 6))
    librosa.display.specshow(D_db, x_axis='time', y_axis='log', sr=sr)
    plt.title("Log-frequency spectrogram")
    plt.colorbar(format="%+2.0f dB")
    plt.xlabel('Time (s)')
    plt.ylabel('Frequency (Hz)')
    plt.show()


# Example usage
input_file = '/Users/nuthan/Music/Ringtones/Muthu.mp3'  # Replace with your input file
extract_frequencies(input_file)
