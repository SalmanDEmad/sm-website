function submitForm() {
    const textTitle = document.getElementById('text-title').value;
    const content = document.getElementById('content').value;
    const imageTitle = document.getElementById('image-title').value;
    const fileInput = document.getElementById('image-video-file');
    
    if (textTitle.trim() === '' && content.trim() === '' && imageTitle.trim() === '' && fileInput.files.length === 0) {
      alert('You cannot send empty fields.');
      return false;
    }
    
    return true;
  }