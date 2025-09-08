SELECT
    ln.name AS network,
    ld.name AS departement,
    lc.name AS commune,
    ls.name AS section,
    lh.name AS hospital_name,
    p.patient_code,
	tmi.first_name,
    tmi.last_name,
    tmi.dob,
    tmi.is_abandoned,
    tmi.abandoned_date,
    tmi.abandoned_reason,
    tp.ddr,
    (tp.ddr + INTERVAL 9 MONTH) as dpa_caculated,
    tp.dpa,
    tp.ptme_enrollment_date,
    lo.name as "Birth Place Planned",
    IF(tp.planned_place_of_birth_hospital_know=1,"Oui",IF(tp.planned_place_of_birth_hospital_know=2,"Non",tp.planned_place_of_birth_hospital_know)) as hospital_known,
    lhp.name as hospital_planned,
    IF(tp.on_arv=1,"Oui","Non") as on_arv,
    tp.created_at as pregnancy_date_added,
    au.email as added_by,
    tp.updated_at as pregnancy_date_updated,
     au1.email as updated_by,
     a.*
FROM
    tracking_pregnancy tp


    LEFT JOIN (


    SELECT
    s.id_patient,
    MIN(cs.date) AS first_session_date_in_13_month,
    MAX(cs.date) AS last_session_date
FROM
    session s
        LEFT JOIN
    club_session cs ON cs.id = s.id_club_session
        LEFT JOIN
    club c ON c.id = cs.id_club
WHERE
    c.club_type = 1 AND s.is_present = 1
        AND cs.date > NOW() - INTERVAL 13 MONTH
GROUP BY s.id_patient

) a on a.id_patient=tp.id_patient_mother
    LEFT join tracking_motherbasicinfo tmi on tmi.id_patient=tp.id_patient_mother
    LEFT JOIN auth_users au on au.id=tp.created_by
    LEFT JOIN auth_users au1 on au1.id=tp.updated_by
    LEFT JOIN patient p on p.id=tp.id_patient_mother
    LEFT JOIN lookup_testing_birth_location lo on lo.id=tp.planned_place_of_birth
    LEFT JOIN lookup_hospital lhp on lhp.id=tp.planned_place_of_birth_hospital

        LEFT JOIN
    lookup_hospital lh ON lh.city_code = p.city_code
        AND lh.hospital_code = p.hospital_code
        LEFT JOIN
    lookup_section ls ON ls.id = lh.section
        LEFT JOIN
    lookup_commune lc ON lc.id = lh.commune
        LEFT JOIN
    lookup_departement ld ON ld.id = lh.departement
        LEFT JOIN
    lookup_network ln ON ln.id = lh.network
WHERE
    ((tp.ddr + INTERVAL 9 MONTH + interval 7 day) > (NOW() - interval 14 day)
        OR tp.dpa > (NOW() - interval 14 day))
        AND ((tp.actual_delivery_date IS NULL)
        OR tp.actual_delivery_date = '0000-00-00')
        AND (tp.termination_of_pregnancy IS NULL
        OR tp.termination_of_pregnancy != 1)


        HAVING commune not in ("Carrefour","Gressier") and departement not in ("Nord-Ouest")