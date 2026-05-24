package tn.esprit.ms_reporting.dto;

import tn.esprit.ms_reporting.entity.enums.SectionType;
import lombok.*;

@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
@Builder
public class SectionDTO {
    private Long id;
    private SectionType sectionType;
    private Boolean included;
}