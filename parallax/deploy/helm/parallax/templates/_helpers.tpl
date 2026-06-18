{{- define "parallax.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "parallax.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "parallax.labels" -}}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/name: {{ include "parallax.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "parallax.selectorLabels" -}}
app.kubernetes.io/name: {{ include "parallax.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "parallax.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "parallax.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "parallax.image" -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag -}}
{{- printf "%s:%s" .Values.image.repository $tag -}}
{{- end -}}

{{- define "parallax.secretName" -}}
{{- if .Values.secrets.existingSecret -}}
{{- .Values.secrets.existingSecret -}}
{{- else -}}
{{- printf "%s-secret" (include "parallax.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- define "parallax.postgresHost" -}}
{{- if .Values.postgres.bundled -}}
{{- printf "%s-postgres" (include "parallax.fullname" .) -}}
{{- else -}}
{{- required "postgres.external.host is required when postgres.bundled=false" .Values.postgres.external.host -}}
{{- end -}}
{{- end -}}

{{- define "parallax.redisHost" -}}
{{- if .Values.redis.bundled -}}
{{- printf "%s-redis" (include "parallax.fullname" .) -}}
{{- else -}}
{{- required "redis.external.host is required when redis.bundled=false" .Values.redis.external.host -}}
{{- end -}}
{{- end -}}

{{- define "parallax.minioServer" -}}
{{- if .Values.minio.bundled -}}
{{- printf "%s-minio:9000" (include "parallax.fullname" .) -}}
{{- else -}}
{{- required "minio.external.server is required when minio.bundled=false" .Values.minio.external.server -}}
{{- end -}}
{{- end -}}

{{- define "parallax.neo4jUri" -}}
{{- if .Values.neo4j.bundled -}}
{{- printf "bolt://%s-neo4j:7687" (include "parallax.fullname" .) -}}
{{- else -}}
{{- required "neo4j.external.uri is required when neo4j.bundled=false" .Values.neo4j.external.uri -}}
{{- end -}}
{{- end -}}

{{- define "parallax.qdrantHost" -}}
{{- if .Values.qdrant.bundled -}}
{{- printf "%s-qdrant" (include "parallax.fullname" .) -}}
{{- else -}}
{{- required "qdrant.external.host is required when qdrant.bundled=false" .Values.qdrant.external.host -}}
{{- end -}}
{{- end -}}
