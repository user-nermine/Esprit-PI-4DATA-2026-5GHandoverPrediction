package tn.esprit.userservice.controller;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import tn.esprit.userservice.entity.AuditLog;
import tn.esprit.userservice.service.AuditLogService;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/audit-logs")
@RequiredArgsConstructor
public class AuditLogController {

    private final AuditLogService auditLogService;

    @GetMapping
    public ResponseEntity<List<AuditLog>> getAllLogs() {
        return ResponseEntity.ok(auditLogService.getAllLogs());
    }

    @GetMapping("/user/{email}")
    public ResponseEntity<List<AuditLog>> getLogsByUser(@PathVariable String email) {
        return ResponseEntity.ok(auditLogService.getLogsByUser(email));
    }

    @GetMapping("/role/{role}")
    public ResponseEntity<List<AuditLog>> getLogsByRole(@PathVariable String role) {
        return ResponseEntity.ok(auditLogService.getLogsByRole(role));
    }

    @GetMapping("/action/{action}")
    public ResponseEntity<List<AuditLog>> getLogsByAction(@PathVariable String action) {
        return ResponseEntity.ok(auditLogService.getLogsByAction(action));
    }

    @GetMapping("/status/{status}")
    public ResponseEntity<List<AuditLog>> getLogsByStatus(@PathVariable String status) {
        return ResponseEntity.ok(auditLogService.getLogsByStatus(status));
    }

    @GetMapping("/class/{className}")
    public ResponseEntity<List<AuditLog>> getLogsByClass(@PathVariable String className) {
        return ResponseEntity.ok(auditLogService.getLogsByClass(className));
    }

    @GetMapping("/recent/{days}")
    public ResponseEntity<List<AuditLog>> getRecentLogs(@PathVariable int days) {
        return ResponseEntity.ok(auditLogService.getRecentLogs(days));
    }

    @DeleteMapping("/cleanup/{days}")
    public ResponseEntity<Map<String, String>> cleanupOldLogs(@PathVariable int days) {
        auditLogService.deleteLogsOlderThan(days);
        Map<String, String> response = new HashMap<>();
        response.put("message", "Deleted logs older than " + days + " days");
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/user/{email}")
    public ResponseEntity<Map<String, String>> deleteLogsByUser(@PathVariable String email) {
        auditLogService.deleteLogsByUser(email);
        Map<String, String> response = new HashMap<>();
        response.put("message", "Deleted all logs for user: " + email);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/stats/count/{status}")
    public ResponseEntity<Map<String, Long>> countByStatus(@PathVariable String status) {
        long count = auditLogService.countLogsByStatus(status);
        Map<String, Long> response = new HashMap<>();
        response.put("count", count);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/stats/avg-time/{methodName}")
    public ResponseEntity<Map<String, Object>> getAverageExecutionTime(@PathVariable String methodName) {
        Double avgTime = auditLogService.getAverageExecutionTimeByMethod(methodName);
        Map<String, Object> response = new HashMap<>();
        response.put("methodName", methodName);
        response.put("averageExecutionTimeMs", avgTime != null ? avgTime : 0);
        return ResponseEntity.ok(response);
    }
}
