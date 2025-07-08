import numpy as np
from scipy.signal import find_peaks

def detect_pqrst(buffer, fs=50):
    """
    Detects and returns the indices of P, Q, R, S, and T waves in an ECG buffer.
    Args:
        buffer (list or np.ndarray): The ECG signal data.
        fs (int): Sampling frequency in Hz.
    Returns:
        List of dicts: Each dict contains indices for 'P', 'Q', 'R', 'S', 'T' for each detected heartbeat.
    """
    results = []
    if len(buffer) < 10:
        return results
    r_peaks, _ = find_peaks(buffer, distance=fs/2, height=np.mean(buffer) + np.std(buffer)*0.5)
    for r in r_peaks:
        # Q point: min before R
        q_search_start = max(r - 10, 0)
        q_search_end = r
        q_point = None
        if q_search_end > q_search_start:
            q_point = np.argmin(buffer[q_search_start:q_search_end]) + q_search_start
        # S point: min after R
        s_search_start = r
        s_search_end = min(r + 10, len(buffer))
        s_point = None
        if s_search_end > s_search_start:
            s_point = np.argmin(buffer[s_search_start:s_search_end]) + s_search_start
        # P point: max before Q
        p_point = None
        if q_point is not None:
            p_search_start = max(q_point - int(0.2 * fs), 0)
            p_search_end = max(q_point - int(0.1 * fs), 0)
            if p_search_end > p_search_start:
                p_point = np.argmax(buffer[p_search_start:p_search_end]) + p_search_start
        # T point: max after S
        t_point = None
        if s_point is not None:
            t_search_start = s_point + int(0.15 * fs)
            t_search_end = min(s_point + int(0.35 * fs), len(buffer))
            if t_search_end > t_search_start:
                t_point = np.argmax(buffer[t_search_start:t_search_end]) + t_search_start
        results.append({
            'P': p_point,
            'Q': q_point,
            'R': r,
            'S': s_point,
            'T': t_point
        })
    return results

if __name__ == "__main__":
    # Example: create a fake ECG-like signal for demonstration
    import matplotlib.pyplot as plt
    t = np.linspace(0, 5, 5*50)  # 5 seconds at 50 Hz
    # Simulate a simple ECG: sum of sinusoids + noise
    ecg = 0.6 * np.sin(2 * np.pi * 1.2 * t) + 0.2 * np.sin(2 * np.pi * 2.4 * t) + 0.1 * np.random.randn(len(t))
    # Add a few sharp R peaks
    for i in range(10, len(ecg), 50):
        if i+1 < len(ecg):
            ecg[i] += 1.5
    points = detect_pqrst(ecg, fs=50)
    print("Detected PQRST points:")
    for beat in points:
        print(beat)
    # Plot for visual check
    plt.plot(ecg, label='ECG')
    for beat in points:
        for label, idx in beat.items():
            if idx is not None:
                plt.plot(idx, ecg[idx], 'o', label=label)
    plt.legend()
    plt.title('ECG with Detected PQRST Points')
    plt.show()
