"""Chuan hoa ten ky nang.

Hai viec chinh:
1. Gop cac bien the ve mot ten chuan: "ReactJS", "React.js", "react" -> "React".
2. Loc bo nhan rac lay nham tu menu/dieu huong cua trang web
   (vd "Việc làm IT", "Xem thêm", "Tất cả").
"""
from __future__ import annotations

import re
import unicodedata


def _key(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9+#.]", "", stripped.lower())


# ten chuan -> cac bien the
_CANONICAL: dict[str, tuple[str, ...]] = {
    "JavaScript": ("javascript", "js", "es6"),
    "TypeScript": ("typescript", "ts"),
    "React": ("react", "reactjs", "react.js", "reactnative"),
    "Vue.js": ("vue", "vuejs", "vue.js"),
    "Angular": ("angular", "angularjs"),
    "Node.js": ("node", "nodejs", "node.js"),
    "Java": ("java", "corejava"),
    "Spring": ("spring", "springboot", "spring-boot"),
    "Python": ("python", "py"),
    "Django": ("django",),
    "PHP": ("php",),
    "Laravel": ("laravel",),
    ".NET": (".net", "dotnet", "net", "aspnet", "asp.net", "c#.net"),
    "C#": ("c#", "csharp"),
    "C++": ("c++", "cpp"),
    "Golang": ("go", "golang"),
    "Ruby": ("ruby", "rubyonrails", "rails"),
    "Kotlin": ("kotlin",),
    "Swift": ("swift", "ios"),
    "Android": ("android",),
    "Flutter": ("flutter", "dart"),
    "SQL": ("sql", "tsql", "plsql"),
    "MySQL": ("mysql",),
    "PostgreSQL": ("postgresql", "postgres"),
    "SQL Server": ("sqlserver", "mssql", "microsoftsqlserver"),
    "Oracle": ("oracle", "oracledb"),
    "MongoDB": ("mongodb", "mongo"),
    "Redis": ("redis",),
    "Elasticsearch": ("elasticsearch", "elk"),
    "Kafka": ("kafka", "apachekafka"),
    "Spark": ("spark", "apachespark", "pyspark"),
    "Hadoop": ("hadoop",),
    "Airflow": ("airflow", "apacheairflow"),
    "ETL": ("etl", "elt"),
    "Data Warehouse": ("datawarehouse", "datawarehousing", "dwh"),
    "Data Engineer": ("dataengineer", "dataengineering"),
    "Data Analyst": ("dataanalyst", "dataanalysis"),
    "Machine Learning": ("machinelearning", "ml"),
    "Deep Learning": ("deeplearning", "dl"),
    "Computer Vision": ("computervision", "cv"),
    "NLP": ("nlp", "naturallanguageprocessing"),
    "Power BI": ("powerbi",),
    "Tableau": ("tableau",),
    "Excel": ("excel",),
    "AWS": ("aws", "amazonwebservices"),
    "Azure": ("azure", "microsoftazure"),
    "GCP": ("gcp", "googlecloud", "googlecloudplatform"),
    "Docker": ("docker",),
    "Kubernetes": ("kubernetes", "k8s"),
    "Terraform": ("terraform",),
    "CI/CD": ("cicd", "ci/cd", "jenkins", "gitlabci"),
    "Linux": ("linux", "ubuntu", "centos"),
    "Git": ("git", "github", "gitlab"),
    "REST API": ("api", "restapi", "restfulapi", "rest"),
    "Microservices": ("microservice", "microservices"),
    "QA/QC": ("qa", "qc", "tester", "qaqc", "manualtest", "automationtest"),
    "Business Analyst": ("ba", "businessanalyst"),
    "Project Manager": ("pm", "projectmanager"),
    "UI/UX": ("uiux", "ui/ux", "ux", "ui", "figma"),
    "Agile/Scrum": ("agile", "scrum"),
    "English": ("english", "tienganh"),
    "Japanese": ("japanese", "tiengnhat"),
    "Korean": ("korean", "tienghan"),
}

_LOOKUP: dict[str, str] = {}
for canonical, variants in _CANONICAL.items():
    _LOOKUP[_key(canonical)] = canonical
    for v in variants:
        _LOOKUP[_key(v)] = canonical

# Nhan lay nham tu menu / dieu huong, khong phai ky nang
_NOISE_PATTERNS = re.compile(
    r"(viec lam|tim viec|xem them|tat ca|cong ty|tuyen dung|luong|dang nhap|dang ky|"
    r"all jobs|view all|see more|sign in|jobs in|companies|blog|top |bao cao)",
    re.IGNORECASE,
)


def _denorm(text: str) -> str:
    text = text.replace("Đ", "D").replace("đ", "d")
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn").lower()


def normalize_skill(raw: str) -> str | None:
    raw = (raw or "").strip(" ,;/|·•\t")
    if not raw or len(raw) > 40:
        return None
    if _NOISE_PATTERNS.search(_denorm(raw)):
        return None
    canonical = _LOOKUP.get(_key(raw))
    if canonical:
        return canonical
    if len(raw) < 2:
        return None
    # Chua co trong tu dien -> giu nguyen nhung chuan hoa hoa/thuong nhe
    return raw if raw.isupper() else raw.title() if raw.islower() else raw


def normalize_skills(raws: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in raws or []:
        skill = normalize_skill(raw)
        if skill and skill not in out:
            out.append(skill)
    return out
