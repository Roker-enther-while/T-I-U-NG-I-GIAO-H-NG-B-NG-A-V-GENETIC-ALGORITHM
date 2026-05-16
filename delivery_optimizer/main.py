import sys
import os

# Thêm thư mục gốc vào path để import các module local
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.generator import generate_points
from graph.graph import build_graph
from graph.distance import build_distance_matrix
from algorithms.genetic import run_ga
from visualization.display import draw_map, draw_route, print_stats, plot_convergence

import sys
sys.stdout.reconfigure(encoding='utf-8')
from gui import DeliveryApp

def main():
    print("--- KHỞI CHẠY GIAO DIỆN TỐI ƯU GIAO HÀNG ---")
    app = DeliveryApp()
    app.mainloop()

if __name__ == "__main__":
    main()
