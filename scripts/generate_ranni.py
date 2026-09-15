import os
import requests
from PIL import Image, ImageDraw

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
        "variables": {"login": USERNAME},
    },
    headers=headers,
)

response.raise_for_status()

data = response.json()

if "errors" in data:
    raise RuntimeError(data["errors"])

weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]

# Configurações do gráfico
CELL_SIZE = 12
GAP = 3

WIDTH = len(weeks) * (CELL_SIZE + GAP)
HEIGHT = 7 * (CELL_SIZE + GAP)

image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)

for x, week in enumerate(weeks):
    for y, day in enumerate(week["contributionDays"]):
        color = day["color"]

        px = x * (CELL_SIZE + GAP)
        py = y * (CELL_SIZE + GAP)

        draw.rounded_rectangle(
            [
                px,
                py,
                px + CELL_SIZE,
                py + CELL_SIZE,
            ],
            radius=2,
            fill=color,
        )

output = "generated/ranni-contributions.gif"

os.makedirs("generated", exist_ok=True)

image.convert("P", palette=Image.ADAPTIVE).save(
    output,
    save_all=True,
    duration=100,
    loop=0,
)

print(f"Gráfico gerado em: {output}")
