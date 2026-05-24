// EngineerObservationRepository.java
package tn.esprit.ms_reporting.repository;

import tn.esprit.ms_reporting.entity.EngineerObservation;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface EngineerObservationRepository extends JpaRepository<EngineerObservation, Long> {
    List<EngineerObservation> findByReportId(Long reportId);
}