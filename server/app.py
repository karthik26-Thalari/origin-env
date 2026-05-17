from openenv.core.env_server.http_server import create_app
try:
    from ..models import OriginAction, OriginObservation
    from .origin_env_environment import OriginEnvironment
except ImportError:
    from models import OriginAction, OriginObservation
    from server.origin_env_environment import OriginEnvironment

app = create_app(
    OriginEnvironment,
    OriginAction,
    OriginObservation,
    env_name='origin_env',
    max_concurrent_envs=1,
)

def main(host='0.0.0.0', port=8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == '__main__':
    main()
