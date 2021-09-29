import math
import argparse


def make_base(width: float, height: float) -> list[float]:
    """outputs the points for a hexagon centered on 0, 0 with the specified width and
        height. for a regular hexagon, height should be sqrt(3)/2 times the width.
        points go clockwise starting from the leftmost. the top and bottom sides are
        parallel to the the x-axis."""
    return [(-width / 2, 0),
            (-width/4, -height/2),
            (width/4, -height/2),
            (width/2, 0),
            (width/4, height/2),
            (-width/4, height/2)]


def make_hexagon(
        centered_on: tuple[float, float],
        radius: float = 10, tilted: bool = False) -> list[tuple[int, int]]:
    width = radius*2
    height = width*(math.sqrt(3)/2)
    points = [(x+centered_on[0], y+centered_on[1]) for x, y in make_base(width, height)]
    if tilted:
        points = [tuple(reversed(x)) for x in points]
    return points


def make_hexagon_ring(
        centered_on: tuple[float, float],
        hex_radius: float = 10,
        ring_radius: float = 15, tilted: bool = True) -> list[list[tuple[int, int]]]:
    centers = make_hexagon(centered_on, ring_radius, tilted)
    points_lists = []
    for center in centers:
        points_lists.append(make_hexagon(center, hex_radius, tilted=(not tilted)))
    return points_lists


def format_point_list(points: list[tuple[int, int]], fill: str = "#E6E6E6FF"):
    points_string = ""
    for point in points:
        points_string += f"{point[0]},{point[1]} "
    return f'<polygon fill="{fill}" points="{points_string.strip()}" />'


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Make a hexagon.')
    parser.add_argument("center_x", metavar="center_x", type=float)
    parser.add_argument("center_y", metavar="center_y", type=float)
    parser.add_argument("radius", metavar="radius", type=float)
    parser.add_argument("--fill", type=str)
    parser.add_argument("--tilted", action="store_true")
    parser.add_argument("--ring", action="store_true")
    parser.add_argument("--ring_radius", type=float)
    args = parser.parse_args()
    if not args.ring:
        print(
            format_point_list(
                make_hexagon((args.center_x, args.center_y),
                             args.radius, args.tilted),
                args.fill))
    else:
        hexes = make_hexagon_ring(
            (args.center_x, args.center_y),
            args.radius, args.ring_radius, args.tilted)
        for hex in hexes:
            print(format_point_list(hex, fill=args.fill))
