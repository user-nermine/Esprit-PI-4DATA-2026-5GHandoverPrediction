// ReportRepository.java
package tn.esprit.ms_reporting.repository;

import tn.esprit.ms_reporting.entity.Report;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface ReportRepository extends JpaRepository<Report, Long> {

    @Query("SELECT r FROM Report r JOIN r.zones z WHERE z.id = :zoneId")
    List<Report> findByZoneId(Long zoneId);
}