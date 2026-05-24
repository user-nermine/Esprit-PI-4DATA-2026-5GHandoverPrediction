package tn.esprit.ms_reporting.service;

import tn.esprit.ms_reporting.dto.ReportRequestDTO;
import tn.esprit.ms_reporting.dto.ReportResponseDTO;
import java.util.List;

public interface IReportService {
    ReportResponseDTO createReport(ReportRequestDTO request);
    ReportResponseDTO getReportById(Long id);
    List<ReportResponseDTO> getAllReports();
    ReportResponseDTO updateReport(Long id, ReportRequestDTO request);
    void deleteReport(Long id);
    byte[] generatePdfReport(Long id);
    List<ReportResponseDTO> getReportsByZone(Long zoneId);
}