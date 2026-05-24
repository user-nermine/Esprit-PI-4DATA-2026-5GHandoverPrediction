package tn.esprit.ms_reporting.dto;

import tn.esprit.ms_reporting.entity.enums.ReportType;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
@Builder
public class ReportResponseDTO {

    private Long id;
    private String title;
    private ReportType reportType;
    private LocalDate periodStart;
    private LocalDate periodEnd;
    private LocalDateTime generatedAt;
    private String generatedBy;
    private String status;
    private String filePath;
    private List<String> zoneNames;
    private List<SectionDTO> sections;
    private String engineerObservation;
}