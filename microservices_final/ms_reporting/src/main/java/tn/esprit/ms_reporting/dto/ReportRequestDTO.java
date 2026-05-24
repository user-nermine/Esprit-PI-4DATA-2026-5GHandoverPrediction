package tn.esprit.ms_reporting.dto;

import tn.esprit.ms_reporting.entity.enums.ReportType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.*;
import java.time.LocalDate;
import java.util.List;

@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
@Builder
public class ReportRequestDTO {

    @NotBlank(message = "Le titre est obligatoire")
    private String title;

    @NotNull(message = "Le type de rapport est obligatoire")
    private ReportType reportType;

    @NotNull
    private LocalDate periodStart;

    @NotNull
    private LocalDate periodEnd;

    private List<Long> zoneIds;
    private List<SectionDTO> sections;
    private String engineerObservation;
    private String engineerName;

}