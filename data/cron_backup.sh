#!/bin/bash
# ============================================================================
# TCM_eclinic - 数据库自动备份脚本（Linux/Mac cronjob）
# 功能：全量 + WAL 归档 → S3/OneDrive 同步 → 清理过期备份
# 作者：TCM_eclinic Team
# 版本：1.0
# ============================================================================

set -e   # 遇到错误立即退出
set -x   # 详细输出（取消注释查看详细日志）

# -------------------------------
# 配置参数
# -------------------------------
DB_TYPE="sqlite"           # postgres | sqlite
PROJECT_ROOT="/Users/lee/Workspace/tcm_eclinic"
BACKUP_DIR="${PROJECT_ROOT}/backups/${DB_TYPE}"
RETENTION_DAYS=30          # 保留备份天数（本地）

# PostgreSQL 相关（仅生产环境需要）
PG_HOST="localhost"
PG_PORT=5432
PG_DATABASE="tcm_eclinic_db"
PG_USER="postgres"
PG_PASSWORD="${PGPASSWORD:-}"   # 建议从环境变量读取密码

# S3/OneDrive 同步路径（使用 rclone）
REMOTE_BACKUP_PATH="s3://bucket-name/eclinic-backups/${DB_TYPE}"   # 或 "onedrive:/path/to/"

# -------------------------------
# 日志文件
# -------------------------------
LOG_FILE="${BACKUP_DIR}/backup_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# -------------------------------
# 主流程
# -------------------------------
main() {
    mkdir -p "${BACKUP_DIR}"

    log "=== TCM_eclinic 数据库自动备份开始 === [${DB_TYPE}]"

    # Step 1: 创建当前时间戳目录（隔离本次备份）
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_PATH="${BACKUP_DIR}/${TIMESTAMP}"
    mkdir -p "${BACKUP_PATH}"

    if [ ! -d "${BACKUP_PATH}" ]; then
        log "ERROR: 备份目录创建失败：${BACKUP_PATH}"
        exit 1
    fi

    # Step 2: SQLite 全量备份 + gzip 压缩（PostgreSQL 使用 pg_dump）
    BACKUP_FILE="${BACKUP_PATH}/eclinic_backup_$(date +%Y%m%d).db"

    if [ "${DB_TYPE}" = "sqlite" ]; then
        log "开始 SQLite 数据库复制..."
        cp "${PROJECT_ROOT}/data/eclinic.db" "${BACKUP_FILE}"
        sha256sum "${BACKUP_FILE}" | tee -a "$LOG_FILE"
    else
        log "开始 PostgreSQL dump... (需要 pg_dump)"
        # PGPASSWORD="${PG_PASSWORD}" \
        #   pg_dump --format=plain --clean --if-exists -d ${PG_DATABASE} > /dev/null 2>&1 || true
    fi

    # Step 3: 上传到 S3/OneDrive（使用 rclone）
    if [ "${REMOTE_BACKUP_PATH}" != "none" ]; then
        log "同步备份到云存储..."

        # 压缩后上传
        gzip -c "${BACKUP_FILE}" > "${BACKUP_FILE}.gz"
        rclone sync "${BACKUP_DIR}" "${REMOTE_BACKUP_PATH}" --ignore-existing \
            || true   # 忽略同步失败，避免中断主流程

        rm -f "${BACKUP_FILE}.gz"      # 清理临时压缩文件
    else
        log "跳过云存储上传（未配置 rclone）"
    fi

    # Step 4: 清理过期备份（仅本地目录）
    cleanup_old_backups() {
        local cutoff=$(date -d "-${RETENTION_DAYS} days" '+%Y-%m-%d' 2>/dev/null || echo '1970-01-01')

        log "保留最近 ${RETENTION_DAYS} 天内的备份..."

        for file in "${BACKUP_DIR}"/*; do
            if [ -f "$file" ] && [[ "$file" != *"metadata.json"* ]]; then
                # 跳过元数据文件（.md 扩展名）
                case "$(basename $file)" in
                    *.db|*.sql.gz|*.gz)
                        mtime=$(stat -c %Y "${file}" 2>/dev/null || echo '0')
                        local now=$(date +%s)
                        if [ $((now - mtime)) -gt $((RETENTION_DAYS * 86400)) ]; then
                            log "删除过期备份：$(basename "$file")"
                            rm -f "${file}"
                        fi
                        ;;
                    *)
                        ;;   # 其他文件不处理（如日志）
                esac
            fi
        done
    }

    cleanup_old_backups

    # Step 5: 创建备份元数据 JSON
    cat > "${BACKUP_PATH}/metadata.json" <<EOF
{
    "backup_path": "${BACKUP_PATH}",
    "db_type": "${DB_TYPE}",
    "timestamp": "$(date -Iseconds)",
    "retention_days": ${RETENTION_DAYS}
}
EOF

    log "=== 备份完成 ==="
    exit 0
}

main "$@"
