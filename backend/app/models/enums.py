"""
统一的枚举定义
避免在多个模块中重复定义枚举类型
"""
import enum


class FileStatus(enum.Enum):
    """文件解析状态"""
    PENDING = 'pending'
    PARSING = 'parsing'
    PARSED = 'parsed'
    PARSE_FAILED = 'parse_failed'


class BackendType(enum.Enum):
    """解析后端类型（用于 File 模型）"""
    PIPELINE = 'pipeline'
    VLM = 'vlm'
    HYBRID = 'hybrid'


class SettingsBackendType(enum.Enum):
    """设置中的后端类型（更详细的配置）"""
    PIPELINE = 'pipeline'
    VLM_HTTP_CLIENT = 'vlm-http-client'
    HYBRID_HTTP_CLIENT = 'hybrid-http-client'

    def to_file_backend(self) -> BackendType:
        """转换为文件后端类型"""
        if self == SettingsBackendType.PIPELINE:
            return BackendType.PIPELINE
        elif self == SettingsBackendType.HYBRID_HTTP_CLIENT:
            return BackendType.HYBRID
        else:
            # 所有 VLM 变体都映射为 VLM
            return BackendType.VLM
