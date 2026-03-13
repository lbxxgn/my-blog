"""Backend Tasks Package"""
from .image_optimization_task import optimization_queue, queue_image_optimization

__all__ = [
    'optimization_queue',
    'queue_image_optimization',
]
