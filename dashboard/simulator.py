import random
import time
from dataclasses import dataclass, asdict
from typing import List, Dict

from src.config import settings


@dataclass
class BikeState:
    id: int
    x_m: float
    y_m: float
    status: str
    battery: int
    last_update: float


class Simulator:
    """Simula posições e estados de motos no pátio.

    A simulação é determinística por execução e pequena, adequada para uso
    dentro do Streamlit app. Não depende de hardware.
    """

    POSSIBLE_STATUSES = ["idle", "in_use", "stopped", "maintenance"]

    def __init__(self, n_bikes: int = 8, seed: int | None = None):
        self.n = n_bikes
        self.rng = random.Random(seed)
        self.bikes: List[BikeState] = []
        # full map size in meters (default)
        self.map_w_m = settings.map_size_meters
        # optional allowed bounding box in meters: (xmin, xmax, ymin, ymax)
        self.allowed_bbox_m: tuple | None = None
        self._init_bikes()

    def _init_bikes(self):
        now = time.time()
        for i in range(self.n):
            if self.allowed_bbox_m:
                xmin, xmax, ymin, ymax = self.allowed_bbox_m
                x = self.rng.uniform(xmin, xmax)
                y = self.rng.uniform(ymin, ymax)
            else:
                x = self.rng.uniform(0, self.map_w_m)
                y = self.rng.uniform(0, self.map_w_m)
            status = self.rng.choice(self.POSSIBLE_STATUSES)
            battery = self.rng.randint(40, 100)
            self.bikes.append(BikeState(i + 1, x, y, status, battery, now))

    def step(self, dt: float = 1.0):
        """Avança a simulação em dt segundos: move algumas motos, altera estados."""
        now = time.time()
        for b in self.bikes:
            # battery drain
            b.battery = max(0, b.battery - self.rng.randint(0, 2))

            # occasional status changes
            if self.rng.random() < 0.05:
                b.status = self.rng.choice(self.POSSIBLE_STATUSES)

            # movement for bikes that are in_use
            if b.status == "in_use" or (self.rng.random() < 0.1 and b.status == "idle"):
                angle = self.rng.uniform(0, 2 * 3.1415926)
                speed_m = self.rng.uniform(0.0, 0.5)  # m per step
                b.x_m += speed_m * self.rng.uniform(0.5, 1.0) * self.rng.choice([-1, 1]) * self.rng.random()
                b.y_m += speed_m * self.rng.uniform(0.5, 1.0) * self.rng.choice([-1, 1]) * self.rng.random()

            # keep in bounds
            if self.allowed_bbox_m:
                xmin, xmax, ymin, ymax = self.allowed_bbox_m
                b.x_m = max(xmin, min(xmax, b.x_m))
                b.y_m = max(ymin, min(ymax, b.y_m))
            else:
                b.x_m = max(0.0, min(self.map_w_m, b.x_m))
                b.y_m = max(0.0, min(self.map_w_m, b.y_m))

            # maintenance trigger
            if b.battery < 10 and b.status != "maintenance":
                b.status = "maintenance"

            b.last_update = now

    def get_states(self) -> List[Dict]:
        return [asdict(b) for b in self.bikes]

    def set_bike_count(self, n: int):
        if n == self.n:
            return
        self.n = n
        self.bikes = []
        self._init_bikes()

    def set_allowed_bbox(self, bbox: tuple | None):
        """Set an allowed bounding box in meters: (xmin, xmax, ymin, ymax).

        If None, bikes can roam the full map (0..map_w_m).
        """
        self.allowed_bbox_m = bbox
        # clamp existing bikes into bbox if provided
        if bbox is None:
            return
        xmin, xmax, ymin, ymax = bbox
        for b in self.bikes:
            b.x_m = max(xmin, min(xmax, b.x_m))
            b.y_m = max(ymin, min(ymax, b.y_m))
