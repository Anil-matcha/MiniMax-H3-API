# Contributing to Open Higgsfield Popcorn

Thanks for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Make your changes
4. Test your changes
5. Commit with clear messages (`git commit -m "Add: feature description"`)
6. Push to your fork (`git push origin feature/your-feature`)
7. Open a Pull Request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Open-Higgsfield-Popcorn.git
cd Open-Higgsfield-Popcorn

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install pydantic aiohttp python-dotenv

# Add API keys to secrets.py
# Get free Groq key: https://console.groq.com/keys
```

## Testing Your Changes

```bash
# Test the free version
python popcorn_free.py --prompt "test scene" --frames 3

# Test the paid version (if you have MuAPI key)
python popcorn_storyboard.py --prompt "test scene" --frames 3
```

## Code Guidelines

- Follow existing code style
- Add comments for complex logic
- Keep functions focused and readable
- Test before submitting

## Ideas for Contributions

- Add support for more free AI providers
- Improve shot planning algorithms
- Add video compilation from frames
- Create web UI
- Improve documentation
- Add more examples

## Questions?

Open an issue for discussion!
