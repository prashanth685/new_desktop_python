import sys
import math
import numpy as np
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from glumpy import app, gloo, gl
from glumpy.graphics import Mesh
from glumpy.transforms import Trackball

class GlumpyWaterfallWidget(QWidget):
    def __init__(self, parent=None, sample_rate=4096, history=50, nfft=4096):
        super().__init__(parent)
        self.sample_rate = sample_rate
        self.history = history
        self.nfft = nfft

        # Create a glumpy canvas
        self.canvas = app.Canvas(keys='interactive', size=(800, 600), bgcolor='white')
        self.view = Trackball()
        self.canvas.attach(self.view)

        # Initialize frequency axis
        half = nfft // 2
        self.freq_bins = np.linspace(0, sample_rate / 2, half)
        X = np.tile(self.freq_bins, (history, 1))
        Y = np.repeat(np.arange(history), half).reshape(history, half)

        # Flattened mesh data arrays
        positions = np.zeros((history * half, 3), dtype=np.float32)
        positions[:,0] = X.ravel()
        positions[:,1] = Y.ravel()
        positions[:,2] = 0

        # Create face indices for grid mesh
        faces = []
        for i in range(history - 1):
            for j in range(half - 1):
                idx = i * half + j
                faces.append([idx, idx + 1, idx + half])
                faces.append([idx + 1, idx + half + 1, idx + half])
        faces = np.array(faces, dtype=np.uint32)

        # Create GPU mesh
        self.mesh = Mesh(positions=positions, faces=faces, color=(0.2, 0.5, 1, 1), shading='smooth')
        self.mesh.attach(self.view)

        self.fft_history = []

        # Timer to trigger updates
        self.timer = app.Timer('auto', connect=self.on_timer, start=True)

        # Wrap the glumpy canvas in Qt layout
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("GPU‑Accelerated 3D Waterfall (glumpy/OpenGL)"))
        layout.addWidget(self.canvas.native)

    def on_timer(self, dt):
        # Simulate FFT data; replace this with your actual data in production
        mag = np.abs(np.random.randn(self.nfft // 2)) * 0.1
        self.fft_history.append(mag)
        if len(self.fft_history) > self.history:
            self.fft_history.pop(0)

        # Push zeros if history isn't full yet
        M = len(self.fft_history)
        if M < self.history:
            data = np.vstack([np.zeros_like(mag)] * (self.history - M) + self.fft_history)
        else:
            data = np.vstack(self.fft_history)

        # Update mesh heights (z-axis)
        verts = self.mesh.vertices.get_data()
        verts['position'][:,2] = data.ravel()
        self.mesh.vertices.set_data(verts)
        self.canvas.update()

    def on_draw(self, event):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        self.mesh.draw()

class WaterfallFeature(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.addWidget(GlumpyWaterfallWidget(self))
        self.setLayout(layout)

if __name__ == "__main__":
    appQt = QApplication(sys.argv)
    feat = WaterfallFeature()
    feat.show()
    sys.exit(appQt.exec_())
