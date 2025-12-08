# Open Higgsfield Popcorn 🍿

An open-source alternative to **Higgsfield Popcorn**, designed to generate consistent, cinematic storyboards and visual sequences using AI.

## What is Higgsfield Popcorn?

[Higgsfield Popcorn](https://higgsfield.ai) is a powerful AI tool for creators that generates consistent character and environment sequences for storyboards, marketing campaigns, and visual storytelling. It solves a major pain point in AI image generation: **consistency**. It allows users to create 4-8 frames that look like they belong to the same movie or narrative, maintaining character identity and visual style across different shots and angles.

## About This Project

**Open Higgsfield Popcorn** is an open-source implementation inspired by the original tool. It leverages the power of **MuAPI** (using models like `gpt-5-mini` and `nano-banana`) to achieve similar results: creating coherent, multi-frame visual stories from text prompts and reference images.

### Key Features

*   **Consistent Storytelling**: Generates 2-12 frames that maintain visual consistency in style, characters, and lighting.
*   **Auto Mode**: simply provide a prompt (e.g., "detective investigating a crime scene") and let the AI plan and generate the entire sequence.
*   **Manual Mode**: Have full control by specifying the description for each shot individually.
*   **Reference-Driven**: Use character and environment reference images to guide the generation and ensure identity consistency.
*   **Cinematic Planning**: Uses an LLM "Director" to intelligently plan shot types (wide, close-up, etc.) and camera angles based on your narrative context.
*   **Style Control**: Choose from various visual styles (Cinematic Realistic, Anime, Noir, etc.).

## Installation

1.  Clone this repository.
2.  Install dependencies:
    ```bash
    pip install requests python-dotenv pydantic aiohttp
    ```
3.  Configure your API keys:
    *   Rename `secrets.py` or edit it directly.
    *   Add your **MuAPI** key (`MUAPIAPP_API_KEY`). You can get one from [muapi.ai](https://muapi.ai).

## Usage

### Auto Mode
Generate a sequence from a single prompt. The AI will plan the shots for you.

```bash
python popcorn_storyboard.py --prompt "A cyberpunk hacker breaking into a secure server room" --frames 6 --style "cyberpunk neon"
```

### Manual Mode
Define exactly what happens in each frame.

```bash
python popcorn_storyboard.py --manual_shots "wide shot of a spooky house" "close up of a hand opening the door" "interior view of a dusty hallway" --style "horror"
```

### Using References
Upload reference images (e.g., your main character or a specific location) to guide the AI.

```bash
python popcorn_storyboard.py --prompt "A knight fighting a dragon" --references https://example.com/knight.png https://example.com/dragon.png
```

## Options

*   `--prompt`: The main story or scene description (Required for Auto Mode).
*   `--manual_shots`: List of descriptions for each frame (Enables Manual Mode).
*   `--frames`: Number of frames to generate (Default: 6).
*   `--style`: Visual style of the sequence (Default: "cinematic realistic").
*   `--references`: URLs or paths to reference images (Up to 4 recommended).
*   `--output`: Directory to save the results.

## License

This project is open-source and available under the MIT License.
