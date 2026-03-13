"""图片后台优化任务系统"""
import threading
import logging
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from backend.image_processor import generate_image_sizes, get_image_hash
from backend.models import get_db_connection

logger = logging.getLogger(__name__)

class ImageOptimizationQueue:
    """线程安全的图片优化队列"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.executor = ThreadPoolExecutor(max_workers=4)
                cls._instance.queue = Queue()
                cls._instance.processing = False
            return cls._instance

    def enqueue(self, image_path):
        """添加图片到优化队列"""
        self.queue.put(image_path)
        logger.info(f'图片已加入优化队列: {image_path}')

        if not self.processing:
            self._process_queue()

    def _process_queue(self):
        """处理队列中的图片"""
        if self.queue.empty():
            self.processing = False
            return

        self.processing = True
        image_path = self.queue.get()

        # 提交到线程池
        self.executor.submit(self._optimize_image, image_path)

        # 继续处理下一个
        self._process_queue()

    def _optimize_image(self, image_path):
        """优化单张图片"""
        try:
            self._update_status(image_path, 'processing')

            uploads_dir = Path(__file__).parent.parent.parent / 'static' / 'uploads'
            output_dir = uploads_dir / 'optimized'
            output_dir.mkdir(exist_ok=True)

            result = generate_image_sizes(image_path, str(output_dir))

            # 计算文件大小
            original_size = Path(image_path).stat().st_size
            optimized_size = sum(
                Path(p).stat().st_size for p in [
                    result.get('thumbnail'),
                    result.get('medium'),
                    result.get('large')
                ] if p
            )

            self._update_completion(
                image_path,
                result.get('thumbnail'),
                result.get('medium'),
                result.get('large'),
                original_size,
                optimized_size
            )

            logger.info(f'图片优化完成: {image_path}')

        except Exception as e:
            logger.error(f'图片优化失败: {image_path}, 错误: {e}')
            self._update_status(image_path, 'failed', str(e))

    def _update_status(self, image_path, status, error=None):
        """更新优化状态"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE optimized_images
            SET status = ?, error_message = ?
            WHERE original_path = ?
        ''', (status, error, image_path))
        conn.commit()
        conn.close()

    def _update_completion(self, original_path, thumbnail, medium, large,
                          original_size, optimized_size):
        """更新优化完成信息"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE optimized_images
            SET thumbnail_path = ?,
                medium_path = ?,
                large_path = ?,
                original_size = ?,
                optimized_size = ?,
                status = 'completed',
                completed_at = CURRENT_TIMESTAMP
            WHERE original_path = ?
        ''', (thumbnail, medium, large, original_size, optimized_size, original_path))
        conn.commit()
        conn.close()

# 全局实例
optimization_queue = ImageOptimizationQueue()

def queue_image_optimization(image_path):
    """队列化图片优化任务（对外接口）"""
    optimization_queue.enqueue(image_path)
