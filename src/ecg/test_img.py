import json
import matplotlib.pyplot as plt

with open('lead_ii_live.json') as f:
    data = json.load(f)

plt.figure(figsize=(10, 4))
plt.plot(data, color='orange')
plt.title("Lead II - Latest 500 Samples")
plt.xlabel("Sample")
plt.ylabel("Amplitude")
plt.grid(True)
plt.show()