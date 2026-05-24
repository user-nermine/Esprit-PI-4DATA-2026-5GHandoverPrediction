package tn.esprit.ms_reporting.entity;

import tn.esprit.ms_reporting.entity.enums.SectionType;
import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "report_sections")
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
@Builder
public class ReportSection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SectionType sectionType;

    @Column(nullable = false)
    private Boolean included;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    private Report report;
}