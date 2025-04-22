$(function () {
    let mediaRecorder, chunks = [], lastBlob = null;
  
    const $submit = $("#submitBtn");
    const $spinner = $("#spinner");
  
    function enableSubmit() { $submit.prop("disabled", false); }
    function disableSubmit() { $submit.prop("disabled", true); }
  
    function updateSubmitState() {
      const hasText = $("#typedAnswer").val().trim().length > 0;
      if (hasText || lastBlob) enableSubmit(); else disableSubmit();
    }
  
    function toggleRecord() {
      if (!mediaRecorder || mediaRecorder.state === "inactive") {
        navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
          mediaRecorder = new MediaRecorder(stream);
          mediaRecorder.start();
          chunks = [];
          mediaRecorder.ondataavailable = e => chunks.push(e.data);
          mediaRecorder.onstop = () => {
            lastBlob = new Blob(chunks, { type: "audio/webm" });
            $("#playback").removeClass("d-none")
                          .attr("src", URL.createObjectURL(lastBlob));
            $("#recordBtn").hide();
            updateSubmitState();
          };
          $("#recordBtn").text("◼ Stop");
        });
      } else {
        mediaRecorder.stop();
        $("#recordBtn").prop("disabled", true);
      }
    }
  
    $(document).on("click", "#recordBtn", toggleRecord);
    $(document).on("input", "#typedAnswer", updateSubmitState);
  
    function showFeedback(ok, heard) {
      const banner = ok
        ? '<div class="alert alert-success mb-3">Great work!</div>'
        : '<div class="alert alert-danger mb-3">Not quite :(</div>';
      const heardHtml =
        `<p class="fst-italic">We heard: <span class="fw-semibold">${$('<div>').text(heard).html()}</span></p>`;
      $("#feedback").html(banner + heardHtml);
      $("#nextBtn").removeClass("d-none");
    }
  
    $(document).on("click", "#submitBtn", function () {
      disableSubmit();
      $spinner.removeClass("d-none");
  
      const qNum = parseInt(window.location.pathname.split("/").pop(), 10);
      const typed = $("#typedAnswer").val().trim();
      const fd = new FormData();
      fd.append("q", qNum);
      fd.append("typed", typed);
      if (!typed && lastBlob) fd.append("audio", lastBlob, "answer.webm");
  
      $.ajax({
        type: "POST",
        url: "/quiz_submit",
        data: fd,
        processData: false,
        contentType: false,
        success: res => {
          $spinner.addClass("d-none");
          showFeedback(res.correct, res.heard);
        },
        error: () => {
          $spinner.addClass("d-none");
          $("#feedback").html('<div class="alert alert-danger">Error. Please try again.</div>');
          enableSubmit();
        }
      });
    });
  
    $(document).on("click", "#nextBtn", function () {
      const next = parseInt(window.location.pathname.split("/").pop(), 10) + 1;
      window.location.href = `/quiz/${next}`;
    });
  });
  