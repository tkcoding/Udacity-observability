
from flask import Flask, render_template, request

# Monitoring
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
from jaeger_client import Config
# Tracing
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from flask_opentracing import FlaskTracing

app = Flask(__name__)
app.config['MONGO_DBNAME'] = 'example-mongodb'
app.config['MONGO_URI'] = 'mongodb://example-mongodb-svc.default.svc.cluster.local:27017/example-mongodb'

# -- Monitoring: Define Monitoring metrics
metrics = PrometheusMetrics(app)
metrics.info("app_info", "Application info", version="1.0.3")
common_counter = metrics.counter(
    'by_endpoint_counter', 'Request count by endpoints',
    labels={'endpoint': lambda: request.endpoint}
)
record_requests_by_status = metrics.summary(
    'requests_by_status', 'Request latencies by status',
    labels={'status': lambda: request.status_code()}
)

# -- Observability: Prep app for tracing -- 
config = Config(
    config={
        'sampler':
            {
                'type': 'const',
                'param': 1
            },
        'logging': True,
        'reporter_batch_size': 1,
    },
    service_name="frontend",
    validate=True)
jaeger_tracer = config.initialize_tracer()
tracing = FlaskTracing(jaeger_tracer, True, app)

# -- Application Body: Routes and Logic --

@app.route("/")
def homepage():
    with jaeger_tracer.start_span("homepage") as span:
        span.set_tag('message', "homepage")
    return render_template("main.html")

@app.route("/error")
@metrics.summary('requests_by_status_5xx', 'Status Code', labels={
    'code': lambda r: '500'
})
def oops():
    return ":(", 500

metrics.register_default(
    metrics.counter(
        'by_path_counter', 'Request count by request paths',
        labels={'path': lambda: request.path}
    )
)
if __name__ == "__main__":
    app.run()

