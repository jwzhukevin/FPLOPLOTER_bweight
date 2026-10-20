"""Bounded Qt worker lifecycle: one running request and one latest pending request."""

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from gui.tools import DataLoaderThread


class BackgroundLoader(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    status = pyqtSignal(str)
    busy_changed = pyqtSignal()
    idle = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._pending = None
        self._generation = 0
        self._closing = False

    @property
    def busy(self):
        return self._worker is not None or self._pending is not None

    def request(self, filename, mode):
        if self._closing:
            return
        self.cancel()
        self._pending = (self._generation, filename, mode)
        if self._worker is None:
            self._start_pending()
        self.busy_changed.emit()

    def cancel(self):
        self._generation += 1
        self._pending = None
        if self._worker is not None:
            self._worker.requestInterruption()

    def shutdown(self):
        self._closing = True
        self.cancel()

    def _start_pending(self):
        generation, filename, mode = self._pending
        self._pending = None
        worker = DataLoaderThread(filename, mode, self)
        worker.generation = generation
        self._worker = worker
        worker.result.connect(self._receive_result)
        worker.error.connect(self._receive_error)
        worker.status.connect(self._receive_status)
        worker.finished.connect(self._finished)
        worker.start()

    def _is_current(self):
        sender = self.sender()
        return (not self._closing and sender is self._worker and
                sender.generation == self._generation)

    @pyqtSlot(object)
    def _receive_result(self, result):
        if self._is_current():
            self.result.emit(result)

    @pyqtSlot(str)
    def _receive_error(self, message):
        if self._is_current():
            self.error.emit(message)

    @pyqtSlot(str)
    def _receive_status(self, message):
        if self._is_current():
            self.status.emit(message)

    @pyqtSlot()
    def _finished(self):
        worker = self.sender()
        self._worker = None
        worker.deleteLater()
        if self._pending is not None and not self._closing:
            self._start_pending()
        self.busy_changed.emit()
        if not self.busy:
            self.idle.emit()
