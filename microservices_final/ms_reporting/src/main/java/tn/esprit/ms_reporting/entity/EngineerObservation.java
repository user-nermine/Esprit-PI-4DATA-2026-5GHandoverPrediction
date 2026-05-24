package tn.esprit.ms_reporting.entity;

import jakarta.persistence.*;
import lombok.*;
import java.time.LocalDateTime;

@Entity
@Table(name = "engineer_observations")
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor
@Builder
public class EngineerObservation {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(columnDefinition = "TEXT")
    private String content;

    @Column
    private String engineerName;

    @Column
    private LocalDateTime createdAt;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id")
    private Report report;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
    }
}