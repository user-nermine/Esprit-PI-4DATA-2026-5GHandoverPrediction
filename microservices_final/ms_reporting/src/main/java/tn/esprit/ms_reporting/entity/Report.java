package tn.esprit.ms_reporting.entity;

import tn.esprit.ms_reporting.entity.enums.ReportType;
import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "reports")
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
@Builder
public class Report {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private ReportType reportType;

    @Column(nullable = false)
    private LocalDate periodStart;

    @Column(nullable = false)
    private LocalDate periodEnd;

    @Column
    private LocalDateTime generatedAt;

    @Column
    private String generatedBy;

    @Column
    private String filePath;

    @Column
    private String status;

    @ManyToMany
    @JoinTable(
            name = "report_zones",
            joinColumns = @JoinColumn(name = "report_id"),
            inverseJoinColumns = @JoinColumn(name = "zone_id")
    )
    @Builder.Default
    private List<Zone> zones = new ArrayList<>();

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<ReportSection> sections = new ArrayList<>();

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    @Builder.Default
    private List<EngineerObservation> observations = new ArrayList<>();

    @PrePersist
    protected void onCreate() {
        this.generatedAt = LocalDateTime.now();
        this.status = "DRAFT";
    }
}