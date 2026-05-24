package tn.esprit.userservice.repository;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import tn.esprit.userservice.entity.AuditLog;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {

    // Récupérer tous les logs par ordre décroissant
    List<AuditLog> findAllByOrderByTimestampDesc();

    // Par utilisateur
    List<AuditLog> findByUserEmailOrderByTimestampDesc(String userEmail);

    // Par rôle
    List<AuditLog> findByRoleOrderByTimestampDesc(String role);

    // Par méthode (action)
    List<AuditLog> findByMethodNameContainingIgnoreCaseOrderByTimestampDesc(String methodName);

    // Par statut
    List<AuditLog> findByStatusOrderByTimestampDesc(String status);

    // Par classe
    List<AuditLog> findByClassNameOrderByTimestampDesc(String className);

    // Logs après une date
    List<AuditLog> findByTimestampAfterOrderByTimestampDesc(LocalDateTime timestamp);

    // Logs entre deux dates
    List<AuditLog> findByTimestampBetweenOrderByTimestampDesc(LocalDateTime start, LocalDateTime end);

    // Supprimer les logs avant une date (SANS @Transactional ici)
    int deleteByTimestampBefore(LocalDateTime timestamp);

    // Supprimer les logs d'un utilisateur par email (corrigé)
    void deleteByUserEmail(String userEmail);

    // Compter par statut
    long countByStatus(String status);

    // Temps d'exécution moyen par méthode (corrigé: executionTimeMs au lieu de executionTimes)
    @Query("SELECT AVG(a.executionTimeMs) FROM AuditLog a WHERE a.methodName = :methodName")
    Double getAverageExecutionTimeByMethod(@Param("methodName") String methodName);

    // Logs échoués récents
    @Query("SELECT a FROM AuditLog a WHERE a.status = 'FAILED' ORDER BY a.timestamp DESC")
    List<AuditLog> findRecentFailedLogs();

    // Top méthodes les plus lentes
    @Query("SELECT a.methodName, AVG(a.executionTimeMs) as avgTime FROM AuditLog a GROUP BY a.methodName ORDER BY avgTime DESC")
    List<Object[]> findSlowestMethods();
}