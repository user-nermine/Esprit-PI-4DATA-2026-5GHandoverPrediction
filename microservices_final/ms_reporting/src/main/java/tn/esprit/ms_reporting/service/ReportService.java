package tn.esprit.ms_reporting.service;

import tn.esprit.ms_reporting.dto.ReportRequestDTO;
import tn.esprit.ms_reporting.dto.ReportResponseDTO;
import tn.esprit.ms_reporting.dto.SectionDTO;
import tn.esprit.ms_reporting.entity.EngineerObservation;
import tn.esprit.ms_reporting.entity.Report;
import tn.esprit.ms_reporting.entity.ReportSection;
import tn.esprit.ms_reporting.entity.Zone;
import tn.esprit.ms_reporting.repository.EngineerObservationRepository;
import tn.esprit.ms_reporting.repository.ReportRepository;
import tn.esprit.ms_reporting.repository.ZoneRepository;
import tn.esprit.ms_reporting.service.IReportService;

import com.itextpdf.text.Document;
import com.itextpdf.text.Font;
import com.itextpdf.text.Paragraph;
import com.itextpdf.text.pdf.PdfWriter;

import jakarta.persistence.EntityNotFoundException;
import lombok.RequiredArgsConstructor;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.ByteArrayOutputStream;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional
public class ReportService implements IReportService {

    private final ReportRepository reportRepository;
    private final ZoneRepository zoneRepository;
    private final EngineerObservationRepository observationRepository;

    // ─── CREATE ───────────────────────────────────────────────
    @Override
    public ReportResponseDTO createReport(ReportRequestDTO request) {
        Report report = Report.builder()
                .title(request.getTitle())
                .reportType(request.getReportType())
                .periodStart(request.getPeriodStart())
                .periodEnd(request.getPeriodEnd())
                .generatedBy(request.getEngineerName())
                .build();

        if (request.getZoneIds() != null && !request.getZoneIds().isEmpty()) {
            List<Zone> zones = zoneRepository.findAllById(request.getZoneIds());
            report.setZones(zones);
        }

        if (request.getSections() != null) {
            List<ReportSection> sections = request.getSections().stream()
                    .map(dto -> ReportSection.builder()
                            .sectionType(dto.getSectionType())
                            .included(dto.getIncluded())
                            .report(report)
                            .build())
                    .collect(Collectors.toList());
            report.setSections(sections);
        }

        Report saved = reportRepository.save(report);

        if (request.getEngineerObservation() != null
                && !request.getEngineerObservation().isBlank()) {
            EngineerObservation obs = EngineerObservation.builder()
                    .content(request.getEngineerObservation())
                    .engineerName(request.getEngineerName())
                    .report(saved)
                    .build();
            observationRepository.save(obs);
        }

        return toDTO(saved);
    }

    // ─── READ ─────────────────────────────────────────────────
    @Override
    @Transactional(readOnly = true)
    public ReportResponseDTO getReportById(Long id) {
        return toDTO(findOrThrow(id));
    }

    @Override
    @Transactional(readOnly = true)
    public List<ReportResponseDTO> getAllReports() {
        return reportRepository.findAll()
                .stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    // ─── UPDATE ───────────────────────────────────────────────
    @Override
    public ReportResponseDTO updateReport(Long id, ReportRequestDTO request) {
        Report report = findOrThrow(id);
        report.setTitle(request.getTitle());
        report.setReportType(request.getReportType());
        report.setPeriodStart(request.getPeriodStart());
        report.setPeriodEnd(request.getPeriodEnd());
        report.setGeneratedBy(request.getEngineerName());

        if (request.getZoneIds() != null) {
            report.setZones(zoneRepository.findAllById(request.getZoneIds()));
        }

        if (request.getSections() != null) {
            report.getSections().clear();
            request.getSections().forEach(dto ->
                    report.getSections().add(ReportSection.builder()
                            .sectionType(dto.getSectionType())
                            .included(dto.getIncluded())
                            .report(report)
                            .build()));
        }

        return toDTO(reportRepository.save(report));
    }

    // ─── DELETE ───────────────────────────────────────────────
    @Override
    public void deleteReport(Long id) {
        reportRepository.deleteById(id);
    }

    // ─── GENERATE PDF ─────────────────────────────────────────
    @Override
    public byte[] generatePdfReport(Long id) {
        Report report = findOrThrow(id);
        try {
            ByteArrayOutputStream baos = new ByteArrayOutputStream();
            Document doc = new Document();
            PdfWriter.getInstance(doc, baos);
            doc.open();

            Font titleFont = new Font(Font.FontFamily.HELVETICA, 18, Font.BOLD);
            Font normalFont = new Font(Font.FontFamily.HELVETICA, 12);
            Font sectionFont = new Font(Font.FontFamily.HELVETICA, 14, Font.BOLD);

            doc.add(new Paragraph(report.getTitle(), titleFont));
            doc.add(new Paragraph(" "));
            doc.add(new Paragraph("Type: " + report.getReportType(), normalFont));
            doc.add(new Paragraph("Periode: " + report.getPeriodStart()
                    + " -> " + report.getPeriodEnd(), normalFont));
            doc.add(new Paragraph(" "));

            if (report.getZones() != null && !report.getZones().isEmpty()) {
                String zoneNames = report.getZones().stream()
                        .map(Zone::getName)
                        .collect(Collectors.joining(", "));
                doc.add(new Paragraph("Zones: " + zoneNames, normalFont));
                doc.add(new Paragraph(" "));
            }

            doc.add(new Paragraph("Sections incluses:", sectionFont));
            if (report.getSections() != null) {
                for (ReportSection s : report.getSections()) {
                    if (Boolean.TRUE.equals(s.getIncluded())) {
                        doc.add(new Paragraph("  - " + s.getSectionType()
                                .name().replace("_", " "), normalFont));
                    }
                }
            }

            List<EngineerObservation> obs = observationRepository.findByReportId(id);
            if (!obs.isEmpty()) {
                doc.add(new Paragraph(" "));
                doc.add(new Paragraph("Observations Ingenieur:", sectionFont));
                for (EngineerObservation o : obs) {
                    doc.add(new Paragraph(o.getContent(), normalFont));
                }
            }

            doc.close();

            report.setStatus("GENERATED");
            report.setGeneratedAt(LocalDateTime.now());
            reportRepository.save(report);

            return baos.toByteArray();

        } catch (Exception e) {
            throw new RuntimeException("Erreur generation PDF: " + e.getMessage(), e);
        }
    }

    // ─── BY ZONE ──────────────────────────────────────────────
    @Override
    @Transactional(readOnly = true)
    public List<ReportResponseDTO> getReportsByZone(Long zoneId) {
        return reportRepository.findByZoneId(zoneId)
                .stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    // ─── HELPERS ──────────────────────────────────────────────
    private Report findOrThrow(Long id) {
        return reportRepository.findById(id)
                .orElseThrow(() -> new EntityNotFoundException("Report not found: " + id));
    }

    private ReportResponseDTO toDTO(Report r) {
        List<String> zoneNames = r.getZones() == null ? new ArrayList<>() :
                r.getZones().stream().map(Zone::getName).collect(Collectors.toList());

        List<SectionDTO> sectionDTOs = r.getSections() == null ? new ArrayList<>() :
                r.getSections().stream()
                        .map(s -> SectionDTO.builder()
                                .id(s.getId())
                                .sectionType(s.getSectionType())
                                .included(s.getIncluded())
                                .build())
                        .collect(Collectors.toList());

        String obsContent = (r.getObservations() != null && !r.getObservations().isEmpty())
                ? r.getObservations().get(0).getContent() : null;

        return ReportResponseDTO.builder()
                .id(r.getId())
                .title(r.getTitle())
                .reportType(r.getReportType())
                .periodStart(r.getPeriodStart())
                .periodEnd(r.getPeriodEnd())
                .generatedAt(r.getGeneratedAt())
                .generatedBy(r.getGeneratedBy())
                .status(r.getStatus())
                .filePath(r.getFilePath())
                .zoneNames(zoneNames)
                .sections(sectionDTOs)
                .engineerObservation(obsContent)
                .build();
    }
}
