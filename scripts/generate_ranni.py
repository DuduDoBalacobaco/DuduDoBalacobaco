import os
import random
import requests
from PIL import Image, ImageDraw, ImageFilter


# ============================================================
# GITHUB
# ============================================================

TOKEN = os.environ["GH_TOKEN"]
USERNAME = os.environ["GITHUB_USERNAME"]

API_URL = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


response = requests.post(
    API_URL,
    json={
        "query": QUERY,
        "variables": {
            "login": USERNAME
        },
    },
    headers=headers,
)

response.raise_for_status()

data = response.json()

if "errors" in data:
    raise RuntimeError(data["errors"])


weeks = data["data"]["user"]["contributionsCollection"][
    "contributionCalendar"
]["weeks"]


# ============================================================
# CONFIGURAÇÕES
# ============================================================

CELL_SIZE = 13
GAP = 3

CELL_STEP = CELL_SIZE + GAP

GRAPH_WIDTH = len(weeks) * CELL_STEP
GRAPH_HEIGHT = 7 * CELL_STEP

# Quantidade de frames
FRAMES = 72

# Velocidade da animação
FRAME_DURATION = 70

# Cor dos quadrados atingidos
BLUE = (70, 180, 255, 255)

# Cor da estrela
STAR_COLOR = (220, 245, 255, 255)

# Cor do brilho
GLOW_COLOR = (80, 190, 255, 130)


# ============================================================
# CARREGAR RANNI
# ============================================================

ranni_file = Image.open("assets/ranni.gif")

# IMPORTANTE:
# O GIF pode ter vários frames.
# Pegamos SOMENTE o primeiro.
ranni_file.seek(0)

# Faz uma cópia independente do GIF.
# Depois disso não usamos mais o arquivo animado.
ranni = ranni_file.convert("RGBA").copy()


# ============================================================
# RECORTAR A RANNI
# ============================================================

# Recorte da imagem original.
#
# A imagem enviada possui bastante espaço preto.
# Esse recorte pega a região onde a Ranni está.
ranni = ranni.crop(
    (320, 490, 490, 811)
)


# ============================================================
# REMOVER FUNDO PRETO
# ============================================================

pixels = ranni.load()

for y in range(ranni.height):

    for x in range(ranni.width):

        r, g, b, a = pixels[x, y]

        brightness = r + g + b

        # Preto completamente transparente
        if brightness < 80:

            pixels[x, y] = (
                0,
                0,
                0,
                0,
            )

        # Transição suave
        elif brightness < 140:

            alpha = int(
                (brightness - 80)
                / 60
                * 255
            )

            pixels[x, y] = (
                r,
                g,
                b,
                alpha,
            )


# ============================================================
# CORTAR ESPAÇO TRANSPARENTE
# ============================================================

bbox = ranni.getbbox()

if bbox:

    ranni = ranni.crop(bbox)


# ============================================================
# TAMANHO DA RANNI
# ============================================================

TARGET_HEIGHT = 92

ratio = TARGET_HEIGHT / ranni.height

new_width = int(
    ranni.width * ratio
)

ranni = ranni.resize(
    (
        new_width,
        TARGET_HEIGHT,
    ),
    Image.Resampling.LANCZOS,
)


# ============================================================
# POSIÇÃO DA RANNI
# ============================================================

ranni_x = (
    GRAPH_WIDTH - ranni.width
) // 2

ranni_y = (
    GRAPH_HEIGHT - ranni.height
) // 2


# ============================================================
# CÉLULAS DO GRÁFICO
# ============================================================

cells = []


for x, week in enumerate(weeks):

    for y, day in enumerate(
        week["contributionDays"]
    ):

        px = x * CELL_STEP
        py = y * CELL_STEP

        cells.append(
            {
                "x": px,
                "y": py,
                "color": day["color"],
                "count": day["contributionCount"],
            }
        )


# ============================================================
# ESCOLHER ALVOS DAS ESTRELAS
# ============================================================

targets = [
    cell
    for cell in cells
    if cell["count"] > 0
]


# Deixa os destinos sempre iguais
# entre uma execução e outra.
random.seed(42)

random.shuffle(targets)

# Quantidade de estrelas
targets = targets[:16]


# ============================================================
# CENTRO DE UMA CÉLULA
# ============================================================

def cell_center(cell):

    return (
        cell["x"] + CELL_SIZE // 2,
        cell["y"] + CELL_SIZE // 2,
    )


# ============================================================
# DESENHAR ESTRELA
# ============================================================

def draw_star(
    image,
    x,
    y,
    size=5,
):

    # --------------------------------------------------------
    # BRILHO
    # --------------------------------------------------------

    glow = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    glow_draw = ImageDraw.Draw(glow)

    glow_draw.ellipse(
        [
            x - size * 2,
            y - size * 2,
            x + size * 2,
            y + size * 2,
        ],
        fill=GLOW_COLOR,
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(6)
    )

    image.alpha_composite(glow)


    # --------------------------------------------------------
    # ESTRELA
    # --------------------------------------------------------

    draw = ImageDraw.Draw(image)

    # Linha horizontal
    draw.line(
        [
            (x - size, y),
            (x + size, y),
        ],
        fill=STAR_COLOR,
        width=2,
    )

    # Linha vertical
    draw.line(
        [
            (x, y - size),
            (x, y + size),
        ],
        fill=STAR_COLOR,
        width=2,
    )

    # Diagonal 1
    draw.line(
        [
            (x - 2, y - 2),
            (x + 2, y + 2),
        ],
        fill=STAR_COLOR,
        width=1,
    )

    # Diagonal 2
    draw.line(
        [
            (x + 2, y - 2),
            (x - 2, y + 2),
        ],
        fill=STAR_COLOR,
        width=1,
    )


# ============================================================
# DESENHAR GRÁFICO
# ============================================================

def draw_graph(activated):

    image = Image.new(
        "RGBA",
        (
            GRAPH_WIDTH,
            GRAPH_HEIGHT,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    draw = ImageDraw.Draw(image)


    for cell in cells:

        # Quadrado atingido
        if cell in activated:

            color = BLUE

        # Cor original do GitHub
        else:

            color = cell["color"]


        x = cell["x"]
        y = cell["y"]


        draw.rounded_rectangle(
            [
                x,
                y,
                x + CELL_SIZE,
                y + CELL_SIZE,
            ],
            radius=3,
            fill=color,
        )


    return image


# ============================================================
# ANIMAÇÃO
# ============================================================

frames = []


# Origem das estrelas:
# exatamente o centro da Ranni.
origin_x = (
    ranni_x
    + ranni.width // 2
)

origin_y = (
    ranni_y
    + ranni.height // 2
)


for frame_number in range(FRAMES):


    # --------------------------------------------------------
    # CICLO DA ANIMAÇÃO
    # --------------------------------------------------------

    cycle_frame = frame_number % 48


    # --------------------------------------------------------
    # QUADRADOS JÁ ATINGIDOS
    # --------------------------------------------------------

    activated = []


    for index, target in enumerate(
        targets
    ):

        hit_frame = (
            10 + index * 2
        )

        if cycle_frame >= hit_frame:

            activated.append(target)


    # --------------------------------------------------------
    # DESENHAR GRÁFICO
    # --------------------------------------------------------

    image = draw_graph(
        activated
    )


    # --------------------------------------------------------
    # ESTRELAS
    # --------------------------------------------------------

    for index, target in enumerate(
        targets
    ):

        start_frame = index * 2

        travel_frames = 12


        progress = (
            cycle_frame
            - start_frame
        ) / travel_frames


        # A estrela está viajando
        if 0 <= progress <= 1:

            target_x, target_y = (
                cell_center(target)
            )


            # ------------------------------------------------
            # MOVIMENTO
            # ------------------------------------------------

            x = (
                origin_x
                + (
                    target_x
                    - origin_x
                )
                * progress
            )


            # Pequena curva na trajetória
            curve = (
                1
                - (
                    2 * progress
                    - 1
                ) ** 2
            )


            y = (
                origin_y
                + (
                    target_y
                    - origin_y
                )
                * progress
                - curve * 8
            )


            draw_star(
                image,
                int(x),
                int(y),
                size=5,
            )


    # ========================================================
    # RANNI FIXA
    # ========================================================

    # IMPORTANTE:
    #
    # Aqui usamos SEMPRE a mesma imagem.
    #
    # Não usamos frame_number.
    # Não usamos outro frame do GIF.
    #
    # Portanto a Ranni não possui animação própria.

    image.alpha_composite(
        ranni,
        (
            ranni_x,
            ranni_y,
        ),
    )


    # --------------------------------------------------------
    # GUARDAR FRAME
    # --------------------------------------------------------

    frames.append(
        image.convert(
            "P",
            palette=Image.Palette.ADAPTIVE,
        )
    )


# ============================================================
# SALVAR GIF
# ============================================================

os.makedirs(
    "generated",
    exist_ok=True,
)


output = (
    "generated/"
    "ranni-contributions.gif"
)


frames[0].save(
    output,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_DURATION,
    loop=0,
    optimize=False,
)


print(
    "Gráfico gerado com sucesso:"
)

print(output)