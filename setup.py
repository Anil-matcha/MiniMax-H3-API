from setuptools import setup


setup(
    name="minimax-h3-api",
    version="0.2.0",
    description="Python SDK for MiniMax H3 video generation through Muapi",
    py_modules=["minimax_h3_api"],
    install_requires=["requests>=2.31.0"],
    python_requires=">=3.9",
)
