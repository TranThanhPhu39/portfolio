"""Efficient-frontier entry point using the tested Markowitz implementation."""
from .markowitz import frontier

efficient_frontier=frontier
__all__=['frontier','efficient_frontier']
