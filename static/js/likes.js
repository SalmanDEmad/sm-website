const likeButtons = document.querySelectorAll('.like-btn');
const dislikeButtons = document.querySelectorAll('.dislike-btn');

likeButtons.forEach((button) => {
  button.addEventListener('click', (event) => {
    event.preventDefault();
    console.log('Like button clicked');
    const postID = button.dataset.postid;
    console.log('Post ID:', postID);
    fetch('/like', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postID }),
    })
      .then((response) => {
        console.log('Fetch executed for like');
        return response.json();
      })
      .then((data) => {
        const parentElement = button.closest('.card-footer');
        const postLikesDislikes = parentElement.querySelector('#post-likes-dislikes');
        const likesDislikes = data.likes - data.dislikes;
        postLikesDislikes.innerHTML = isNaN(likesDislikes) ? 0 : likesDislikes;
        const svgPath = parentElement.querySelector('.like-svg');
        if (svgPath.getAttribute('fill') === 'blue') {
          svgPath.setAttribute('fill', '#555555');
        } else if (svgPath.getAttribute('fill') === '#555555') {
          const dislikeSvg = parentElement.querySelector('.dislike-svg');
          if (dislikeSvg.getAttribute('fill') === 'red') {
            dislikeSvg.setAttribute('fill', '#555555');
          }
          svgPath.setAttribute('fill', 'blue');
        } else {
          // do nothing
        }
        
      });
  });
});



dislikeButtons.forEach((button) => {
  button.addEventListener('click', (event) => {
    event.preventDefault();
    console.log('Dislike button clicked');
    const postID = button.dataset.postid;
    console.log('Post ID:', postID);
    fetch('/dislike', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ post_id: postID }),
    })
      .then((response) => {
        console.log('Fetch executed for dislike');
        return response.json();
      })

      .then((data) => {
        const parentElement = button.closest('.card-footer');
        const postLikesDislikes = parentElement.querySelector('#post-likes-dislikes'); 
        const likesDislikes = data.likes - data.dislikes;
        postLikesDislikes.innerHTML = isNaN(likesDislikes) ? 0 : (likesDislikes < 0 ? likesDislikes : '+' + likesDislikes);

        const svgPath = parentElement.querySelector('.dislike-svg');
        if (svgPath.getAttribute('fill') === 'red') {
          svgPath.setAttribute('fill', '#555555');
        } else if (svgPath.getAttribute('fill') === '#555555') {
          const dislikeSvg = parentElement.querySelector('.like-svg');
          if (dislikeSvg.getAttribute('fill') === 'blue') {
            dislikeSvg.setAttribute('fill', '#555555');
          }
          svgPath.setAttribute('fill', 'red');
        } else {
          // do nothing
        }
      })
      .catch((error) => {
        console.error(error);
      });
  });
});

  
  var deleteButtons = document.querySelectorAll('.delete-btn');

  deleteButtons.forEach(function(deleteButton) {
    deleteButton.addEventListener('click', function(event) {
      event.preventDefault();
      var postId = deleteButton.dataset.deleteid;
      console.log('Post ID:', postId);
  
      var deletePostButton = document.getElementById('deletePostButton');
      deletePostButton.addEventListener('click', function(event) {
        console.log('Delete Post button clicked');
        fetch('/delete-post', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ post_id: postId }),
        })
          .then(function(response) {
            console.log('Fetch executed for delete');
            return response.json();
          })
  
          .then(function(data) {
            if (data.success) {
              var postElement = deleteButton.closest('.post-container');
              if (postElement) {
                var postHeader = postElement.querySelector('.card-header');
                if (postHeader) {
                  postHeader.innerHTML = '<h5 class="card-title">Deleted</h5>';
                } else {
                  console.error('Element not found: .card-header');
                }
  
                var postBody = postElement.querySelector('.card-body');
                if (postBody) {
                  var postImage = postBody.querySelector('#post-image');
                  var postSubtitle = postBody.querySelector('#post-subtitle');
                  if (postImage) {
                    postImage.remove();
                    postBody.innerHTML += '<h5 class="card-subtitle text-muted">[deleted]</h5>';
                  } else if (postSubtitle) {
                    postBody.innerHTML = '<h5 class="card-subtitle text-muted">[deleted]</h5>';
                  } else {
                    console.error('No element found: .card-subtitle or #post-image');
                  }
                } else {
                  console.error('Element not found: .card-body');
                }
  
                var postFooter = postElement.querySelector('.card-footer');
                if (postFooter) {
                  postFooter.innerHTML = '<p>Deleted</p>';
                } else {
                  console.error('Element not found: .card-footer');
                }
  
                var deleteModal = document.getElementById('deleteModal');
                var modal = bootstrap.Modal.getInstance(deleteModal);
                modal.hide();
              } else {
                console.error('Element not found: .post');
              }
            }
          })
  
          .catch(function(error) {
            console.error(error);
          });
      });
    });
  });
  