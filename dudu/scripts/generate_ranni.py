import os
import json
import requests
from PIL import Image, ImageDraw, ImageFilter
from datetime import datetime, timedelta


USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GH_TOKEN"]

OUTPUT = "generated/ranni-contributions.gif"
RANNI_PATH = "assets/ranni.gif"


GRAPHQL_QUERY = """
query {
  viewer {
    login
    contributionsCollection {
      contributionCalendar {
        colors
        weeks {
          contributionDays {
            date
            contributionCount
            color
            weekday
          }
        }
      }
    }
  }
}
"""


def get_contributions():
    response = requests.post(
        "https://api.github.com/graphql",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        json={"query": GRAPHQL_QUERY},
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))

    return data["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]


def load_ranni():
    image = Image.open(RANNI_PATH)

    frames = []

    try:
        frame_count = image.n_frames
    except AttributeError:
        frame_count = 1

    for frame in range(frame_count):
        image.seek(frame)

        frame_image = image.convert("RGBA")

        # Remove fundo preto
        pixels = frame_image.load()

        for y in range(frame_image.height):
            for x in range(frame_image.width):
                r, g, b, a = pixels[x, y]

                if r < 20 and g < 20 and b < 20:
                    pixels[x, y] = (0, 0, 0, 0)

        frames.append(frame_image.copy())

    return frames


def create_graph(calendar):
    weeks = calendar["weeks"]

    # Tamanho dos quadradinhos
    CELL = 12
    GAP = 3

    STEP = CELL + GAP

    columns = len(weeks)
    rows = 7

    width = columns * STEP
    height = rows * STEP

    # Fundo transparente
    graph = Image.new(
        "RGBA",
        (width, height),
        (0, 0, 0, 0)
    )

    draw = ImageDraw.Draw(graph)

    positions = []

    for x, week in enumerate(weeks):
        for day in week["contributionDays"]:

            y = day["weekday"]

            px = x * STEP
            py = y * STEP

            color = day["color"]

            draw.rounded_rectangle(
                [
                    px,
                    py,
                    px + CELL,
                    py + CELL
                ],
                radius=2,
                fill=color
            )

            positions.append({
                "x": px,
                "y": py,
                "color": color,
                "count": day["contributionCount"]
            })

    return graph, positions, CELL


def create_star_layer(size, x, y):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))

    draw = ImageDraw.Draw(layer)

    cx = x
    cy = y

    points = []

    import math

    for i in range(8):
        angle = math.radians(i * 45)

        radius = 8 if i % 2 == 0 else 3

        px = cx + math.cos(angle) * radius
        py = cy + math.sin(angle) * radius

        points.append((px, py))

    draw.polygon(
        points,
        fill=(255, 255, 255, 255)
    )

    glow = layer.filter(
        ImageFilter.GaussianBlur(5)
    )

    result = Image.alpha_composite(glow, layer)

    return result


def resize_ranni(frames, size):
    resized = []

    for frame in frames:
        ratio = size / frame.width

        new_size = (
            int(frame.width * ratio),
            int(frame.height * ratio)
        )

        resized.append(
            frame.resize(
                new_size,
                Image.Resampling.LANCZOS
            )
        )

    return resized


def main():

    os.makedirs("generated", exist_ok=True)

    calendar = get_contributions()

    graph, positions, cell = create_graph(calendar)

    ranni_frames = load_ranni()

    # Ranni ocupa aproximadamente 5 quadradinhos
    ranni_frames = resize_ranni(
        ranni_frames,
        int(cell * 5)
    )

    # Posição central do gráfico
    center_x = graph.width // 2
    center_y = graph.height // 2

    frames = []

    # Número de estrelas que vão sair da Ranni
    star_count = min(30, len(positions))

    selected_positions = positions[
        ::max(1, len(positions) // star_count)
    ][:star_count]

    # Quantos frames para cada estrela
    frames_per_star = 4

    for index in range(
        star_count * frames_per_star
    ):

        frame = graph.copy()

        current_star = index // frames_per_star
        progress = (index % frames_per_star) / frames_per_star

        # Ranni animada
        ranni = ranni_frames[
            index % len(ranni_frames)
        ]

        rx = center_x - ranni.width // 2
        ry = center_y - ranni.height // 2

        frame.alpha_composite(
            ranni,
            (rx, ry)
        )

        # Estrelas já ativadas
        for i in range(current_star):

            target = selected_positions[i]

            star_x = target["x"] + cell // 2
            star_y = target["y"] + cell // 2

            # Transformação visual verde -> azul
            draw = ImageDraw.Draw(frame)

            blue = (65, 130, 255, 255)

            draw.rounded_rectangle(
                [
                    target["x"],
                    target["y"],
                    target["x"] + cell,
                    target["y"] + cell
                ],
                radius=2,
                fill=blue
            )

        # Estrela atual viajando
        if current_star < len(selected_positions):

            target = selected_positions[current_star]

            tx = target["x"] + cell // 2
            ty = target["y"] + cell // 2

            sx = center_x
            sy = center_y

            x = sx + (tx - sx) * progress
            y = sy + (ty - sy) * progress

            star = create_star_layer(
                frame.size,
                x,
                y
            )

            frame = Image.alpha_composite(
                frame,
                star
            )

        frames.append(frame)

    # Último frame: gráfico inteiro + Ranni
    final = graph.copy()

    draw = ImageDraw.Draw(final)

    for position in positions:

        draw.rounded_rectangle(
            [
                position["x"],
                position["y"],
                position["x"] + cell,
                position["y"] + cell
            ],
            radius=2,
            fill=(65, 130, 255, 255)
        )

    ranni = ranni_frames[0]

    final.alpha_composite(
        ranni,
        (
            center_x - ranni.width // 2,
            center_y - ranni.height // 2
        )
    )

    # Segura o final por alguns frames
    for _ in range(12):
        frames.append(final.copy())

    # Salvar GIF
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=120,
        loop=0,
        disposal=2
    )

    print(f"Gerado: {OUTPUT}")


if __name__ == "__main__":
    main()