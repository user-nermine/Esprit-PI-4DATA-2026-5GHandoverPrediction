package tn.esprit.userservice.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tn.esprit.userservice.entity.AuditLog;
import tn.esprit.userservice.repository.AuditLogRepository;

import java.time.LocalDateTime;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class AuditLogService {

    private final AuditLogRepository auditLogRepository;

    @Transactional
    public void saveLog(String userEmail, String className, String methodName,
                        int argsCount, String status, String errorMessage,
                        long executionTime) {
        try {
            AuditLog auditLog = AuditLog.builder()
                    .userEmail(userEmail)
                    .className(className)
                    .methodName(methodName)
                    .argsCount(argsCount)
                    .status(status)
                    .errorMessage(errorMessage)
                    .executionTimeMs(executionTime)
                    .timestamp(LocalDateTime.now())
                    .build();

            auditLogRepository.save(auditLog);
            log.debug("Audit log saved for method: {}.{}", className, methodName);
        } catch (Exception e) {
            log.error("Failed to save audit log: {}", e.getMessage());
        }
    }

    public List<AuditLog> getAllLogs() {
        return auditLogRepository.findAllByOrderByTimestampDesc();
    }

    public List<AuditLog> getLogsByUser(String userEmail) {
        return auditLogRepository.findByUserEmailOrderByTimestampDesc(userEmail);
    }

    public List<AuditLog> getLogsByRole(String role) {
        return auditLogRepository.findByRoleOrderByTimestampDesc(role);
    }

    // ⚠️ AJOUTER CETTE MÉTHODE ⚠️
    public List<AuditLog> getLogsByAction(String action) {
        return auditLogRepository.findByMethodNameContainingIgnoreCaseOrderByTimestampDesc(action);
    }

    public List<AuditLog> getLogsByStatus(String status) {
        return auditLogRepository.findByStatusOrderByTimestampDesc(status);
    }

    public List<AuditLog> getLogsByClass(String className) {
        return auditLogRepository.findByClassNameOrderByTimestampDesc(className);
    }

    public List<AuditLog> getRecentLogs(int days) {
        LocalDateTime since = LocalDateTime.now().minusDays(days);
        return auditLogRepository.findByTimestampAfterOrderByTimestampDesc(since);
    }

    @Transactional
    public void deleteLogsOlderThan(int days) {
        LocalDateTime cutoffDate = LocalDateTime.now().minusDays(days);
        int deletedCount = auditLogRepository.deleteByTimestampBefore(cutoffDate);
        log.info("Deleted {} audit logs older than {} days", deletedCount, days);
    }

    @Transactional
    public void deleteLogsByUser(String userEmail) {
        auditLogRepository.deleteByUserEmail(userEmail);
        log.info("Deleted all audit logs for user: {}", userEmail);
    }

    public long countLogsByStatus(String status) {
        return auditLogRepository.countByStatus(status);
    }

    public Double getAverageExecutionTimeByMethod(String methodName) {
        return auditLogRepository.getAverageExecutionTimeByMethod(methodName);
    }
}