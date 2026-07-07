# Celery autodiscover는 tasks.py를 찾지만, tasks/ 패키지일 때는
# __init__.py에서 서브모듈을 import해야 task가 등록된다.
from .attention_tasks import *  # noqa: F401,F403
from .estimate_tasks import *  # noqa: F401,F403
from .event_group_tasks import *  # noqa: F401,F403
from .insider_tasks import *  # noqa: F401,F403
from .leadership_tasks import *  # noqa: F401,F403
from .neo4j_dirty_sync_tasks import *  # noqa: F401,F403
from .peer_tasks import *  # noqa: F401,F403
from .profile_tasks import *  # noqa: F401,F403
from .relation_tasks import *  # noqa: F401,F403
from .seed_tasks import *  # noqa: F401,F403
from .sensitivity_tasks import *  # noqa: F401,F403
from .sync_tasks import *  # noqa: F401,F403
